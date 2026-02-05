import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta, datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Attendance Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    h1 {
        color: #1f77b4;
        font-weight: 700;
    }
    h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    .upload-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .css-1d391kg {
        padding: 2rem 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Constants
TARGET_WEEKLY_HOURS = 40
WORKING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Weekly Attendance Analytics Dashboard")
    st.markdown("**Real-time workforce monitoring & performance insights**")
with col2:
    st.metric("Target Weekly Hours", f"{TARGET_WEEKLY_HOURS}:00:00", delta="Mon-Fri")

st.divider()

# File upload section
uploaded_file = st.file_uploader(
    "📁 Upload Your Attendance Report (CSV)",
    type=["csv"],
    help="Upload the Trial Month Report.csv file containing attendance data"
)

if uploaded_file:
    try:
        # Load and process data
        with st.spinner("🔄 Processing attendance data..."):
            df = pd.read_csv(uploaded_file)
            
            # Data cleaning and preparation
            df["Date/time"] = pd.to_datetime(df["Date/time"])
            df["Date"] = df["Date/time"].dt.date
            df["Time"] = df["Date/time"].dt.time
            df["Week"] = df["Date/time"].dt.to_period("W-MON").astype(str)
            df["Day"] = df["Date/time"].dt.day_name()
            df["Month"] = df["Date/time"].dt.strftime("%B %Y")
            
            # Filter working days only
            df = df[df["Day"].isin(WORKING_DAYS)]
            
            # Identify In/Out
            df["IO"] = df["Where"].apply(
                lambda x: "In" if "In" in str(x) else ("Out" if "Out" in str(x) else None)
            )
            
            # Daily aggregation
            daily = (
                df.groupby(["User", "Date"])
                .agg(
                    In_Time=("Date/time", lambda x: x[df.loc[x.index, "IO"] == "In"].min()),
                    Out_Time=("Date/time", lambda x: x[df.loc[x.index, "IO"] == "Out"].max()),
                )
                .reset_index()
            )
            
            daily["Working_Hours"] = daily["Out_Time"] - daily["In_Time"]
            daily["Working_Hours"] = daily["Working_Hours"].fillna(timedelta(0))
            daily["Working_Hours_decimal"] = daily["Working_Hours"].dt.total_seconds() / 3600
            daily["Week"] = pd.to_datetime(daily["Date"]).dt.to_period("W-MON").astype(str)
            daily["Month"] = pd.to_datetime(daily["Date"]).dt.strftime("%B %Y")
            
            # Weekly aggregation
            weekly = (
                daily.groupby(["User", "Week"])
                .agg(
                    Actual_Hours=("Working_Hours", "sum"),
                    Days_Worked=("Date", "count"),
                )
                .reset_index()
            )
            
            weekly["Actual_Hours_decimal"] = weekly["Actual_Hours"].dt.total_seconds() / 3600
            weekly["Target_Hours"] = TARGET_WEEKLY_HOURS
            weekly["Gap_Hours"] = weekly["Target_Hours"] - weekly["Actual_Hours_decimal"]
            weekly["Gap_%"] = (weekly["Gap_Hours"] / weekly["Target_Hours"]) * 100
            weekly["Compliance"] = weekly["Actual_Hours_decimal"].apply(
                lambda x: "✅ Met" if x >= TARGET_WEEKLY_HOURS else "⚠️ Below Target"
            )
            weekly["Performance_Score"] = (weekly["Actual_Hours_decimal"] / TARGET_WEEKLY_HOURS * 100).round(1)
            
            # Format for display
            weekly["Actual_Hours_Display"] = weekly["Actual_Hours"].apply(
                lambda x: str(x).split(".")[0]
            )
            
        st.success("✅ Data loaded successfully!")
        
        # Sidebar filters
        st.sidebar.image("https://via.placeholder.com/250x80/667eea/ffffff?text=Attendance+System", use_container_width=True)
        st.sidebar.header("🎯 Filter Controls")
        
        # User filter with "Select All" option
        all_users = sorted(weekly["User"].unique())
        select_all_users = st.sidebar.checkbox("Select All Users", value=True)
        
        if select_all_users:
            selected_user = st.sidebar.multiselect(
                "👤 Select Users",
                all_users,
                default=all_users,
                disabled=True
            )
        else:
            selected_user = st.sidebar.multiselect(
                "👤 Select Users",
                all_users,
                default=all_users
            )
        
        # Week filter
        all_weeks = sorted(weekly["Week"].unique())
        select_all_weeks = st.sidebar.checkbox("Select All Weeks", value=True)
        
        if select_all_weeks:
            selected_week = st.sidebar.multiselect(
                "📅 Select Weeks",
                all_weeks,
                default=all_weeks,
                disabled=True
            )
        else:
            selected_week = st.sidebar.multiselect(
                "📅 Select Weeks",
                all_weeks,
                default=all_weeks
            )
        
        # Performance threshold filter
        st.sidebar.divider()
        st.sidebar.subheader("🎚️ Performance Filter")
        performance_threshold = st.sidebar.slider(
            "Minimum Performance Score (%)",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            help="Filter employees by minimum performance score"
        )
        
        # Apply filters
        filtered = weekly[
            (weekly["User"].isin(selected_user)) &
            (weekly["Week"].isin(selected_week)) &
            (weekly["Performance_Score"] >= performance_threshold)
        ]
        
        # Export options
        st.sidebar.divider()
        st.sidebar.subheader("📥 Export Data")
        export_format = st.sidebar.radio("Select Format", ["CSV", "Excel"])
        
        if st.sidebar.button("📤 Download Report", use_container_width=True):
            if export_format == "CSV":
                csv = filtered.to_csv(index=False)
                st.sidebar.download_button(
                    "💾 Download CSV",
                    csv,
                    "attendance_report.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                # For Excel, we'll create CSV (Excel export requires openpyxl)
                csv = filtered.to_csv(index=False)
                st.sidebar.download_button(
                    "💾 Download CSV (Excel format requires additional setup)",
                    csv,
                    "attendance_report.csv",
                    "text/csv",
                    use_container_width=True
                )
        
        # Main dashboard
        if not filtered.empty:
            # KPI Metrics
            st.subheader("📈 Key Performance Indicators")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            total_actual = filtered['Actual_Hours_decimal'].sum()
            total_target = TARGET_WEEKLY_HOURS * len(filtered)
            avg_gap_pct = filtered['Gap_%'].mean()
            avg_performance = filtered['Performance_Score'].mean()
            compliant_count = len(filtered[filtered['Performance_Score'] >= 100])
            
            with col1:
                st.metric(
                    "Total Hours Worked",
                    f"{total_actual:.1f}h",
                    delta=f"{total_actual - total_target:.1f}h vs target"
                )
            
            with col2:
                st.metric(
                    "Target Hours",
                    f"{total_target:.1f}h",
                    delta=None
                )
            
            with col3:
                st.metric(
                    "Average Gap",
                    f"{avg_gap_pct:.1f}%",
                    delta=f"{-avg_gap_pct:.1f}%" if avg_gap_pct < 0 else f"-{avg_gap_pct:.1f}%",
                    delta_color="inverse"
                )
            
            with col4:
                st.metric(
                    "Avg Performance Score",
                    f"{avg_performance:.1f}%",
                    delta=f"{avg_performance - 100:.1f}% vs target"
                )
            
            with col5:
                compliance_rate = (compliant_count / len(filtered) * 100) if len(filtered) > 0 else 0
                st.metric(
                    "Compliance Rate",
                    f"{compliance_rate:.0f}%",
                    delta=f"{compliant_count}/{len(filtered)} records"
                )
            
            st.divider()
            
            # Tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📅 Weekly Analysis", "👥 User Comparison", "📋 Detailed Data"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🎯 Performance Distribution")
                    
                    # Performance distribution pie chart
                    perf_categories = pd.cut(
                        filtered['Performance_Score'],
                        bins=[0, 80, 95, 100, 150],
                        labels=['Below 80%', '80-95%', '95-100%', 'Above 100%']
                    )
                    perf_dist = perf_categories.value_counts().reset_index()
                    perf_dist.columns = ['Category', 'Count']
                    
                    fig_pie = px.pie(
                        perf_dist,
                        values='Count',
                        names='Category',
                        title='Performance Categories',
                        color_discrete_sequence=px.colors.sequential.RdBu,
                        hole=0.4
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.subheader("📊 Average Hours by User")
                    
                    # Average hours by user
                    user_avg = filtered.groupby('User')['Actual_Hours_decimal'].mean().reset_index()
                    user_avg = user_avg.sort_values('Actual_Hours_decimal', ascending=True)
                    
                    fig_bar = px.bar(
                        user_avg,
                        x='Actual_Hours_decimal',
                        y='User',
                        orientation='h',
                        title='Average Weekly Hours per User',
                        labels={'Actual_Hours_decimal': 'Hours', 'User': 'Employee'},
                        color='Actual_Hours_decimal',
                        color_continuous_scale='Blues'
                    )
                    fig_bar.add_vline(x=TARGET_WEEKLY_HOURS, line_dash="dash", line_color="red", 
                                     annotation_text="Target", annotation_position="top right")
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                # Trend analysis
                st.subheader("📈 Weekly Trend Analysis")
                
                trend_data = filtered.groupby('Week').agg({
                    'Actual_Hours_decimal': 'mean',
                    'Performance_Score': 'mean',
                    'Days_Worked': 'mean'
                }).reset_index()
                
                fig_trend = go.Figure()
                
                fig_trend.add_trace(go.Scatter(
                    x=trend_data['Week'],
                    y=trend_data['Actual_Hours_decimal'],
                    mode='lines+markers',
                    name='Avg Hours',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8)
                ))
                
                fig_trend.add_hline(
                    y=TARGET_WEEKLY_HOURS,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Target (40h)",
                    annotation_position="right"
                )
                
                fig_trend.update_layout(
                    title='Average Weekly Hours Trend',
                    xaxis_title='Week',
                    yaxis_title='Hours',
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
            
            with tab2:
                st.subheader("📅 Week-by-Week Performance Analysis")
                
                # Heatmap of performance by user and week
                heatmap_data = filtered.pivot_table(
                    index='User',
                    columns='Week',
                    values='Performance_Score',
                    aggfunc='mean'
                )
                
                fig_heatmap = px.imshow(
                    heatmap_data,
                    labels=dict(x="Week", y="User", color="Performance Score (%)"),
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    color_continuous_scale='RdYlGn',
                    aspect="auto",
                    title="Performance Heatmap: User vs Week"
                )
                fig_heatmap.update_xaxes(side="bottom")
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Weekly statistics
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Days Worked Distribution")
                    days_dist = filtered['Days_Worked'].value_counts().sort_index().reset_index()
                    days_dist.columns = ['Days', 'Count']
                    
                    fig_days = px.bar(
                        days_dist,
                        x='Days',
                        y='Count',
                        title='Distribution of Working Days per Week',
                        labels={'Days': 'Days Worked', 'Count': 'Frequency'},
                        color='Count',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig_days, use_container_width=True)
                
                with col2:
                    st.subheader("⚠️ Gap Analysis")
                    gap_summary = filtered.groupby('Week')['Gap_Hours'].sum().reset_index()
                    
                    fig_gap = px.bar(
                        gap_summary,
                        x='Week',
                        y='Gap_Hours',
                        title='Total Gap Hours by Week',
                        labels={'Gap_Hours': 'Gap (Hours)', 'Week': 'Week'},
                        color='Gap_Hours',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig_gap, use_container_width=True)
            
            with tab3:
                st.subheader("👥 User Performance Comparison")
                
                # User comparison metrics
                user_summary = filtered.groupby('User').agg({
                    'Actual_Hours_decimal': 'sum',
                    'Performance_Score': 'mean',
                    'Days_Worked': 'sum',
                    'Gap_Hours': 'sum'
                }).reset_index()
                
                user_summary = user_summary.sort_values('Performance_Score', ascending=False)
                
                # Radar chart for top performers
                st.subheader("🏆 Top Performers Radar Analysis")
                
                top_n = st.slider("Select number of top performers to display", 3, min(10, len(user_summary)), 5)
                top_users = user_summary.head(top_n)
                
                # Normalize metrics for radar chart
                top_users['Normalized_Hours'] = (top_users['Actual_Hours_decimal'] / top_users['Actual_Hours_decimal'].max()) * 100
                top_users['Normalized_Days'] = (top_users['Days_Worked'] / top_users['Days_Worked'].max()) * 100
                
                fig_radar = go.Figure()
                
                for _, user in top_users.iterrows():
                    fig_radar.add_trace(go.Scatterpolar(
                        r=[user['Performance_Score'], user['Normalized_Hours'], user['Normalized_Days']],
                        theta=['Performance Score', 'Total Hours', 'Days Worked'],
                        fill='toself',
                        name=user['User']
                    ))
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=True,
                    title="Multi-dimensional Performance Comparison",
                    height=500
                )
                
                st.plotly_chart(fig_radar, use_container_width=True)
                
                # User ranking table
                st.subheader("📊 Complete User Rankings")
                
                user_summary['Rank'] = range(1, len(user_summary) + 1)
                user_summary['Total Hours'] = user_summary['Actual_Hours_decimal'].round(1)
                user_summary['Avg Performance'] = user_summary['Performance_Score'].round(1)
                user_summary['Total Days'] = user_summary['Days_Worked'].astype(int)
                user_summary['Total Gap'] = user_summary['Gap_Hours'].round(1)
                
                display_cols = ['Rank', 'User', 'Total Hours', 'Avg Performance', 'Total Days', 'Total Gap']
                
                st.dataframe(
                    user_summary[display_cols].style.background_gradient(
                        subset=['Avg Performance'],
                        cmap='RdYlGn',
                        vmin=80,
                        vmax=110
                    ),
                    use_container_width=True,
                    height=400
                )
            
            with tab4:
                st.subheader("📋 Detailed Weekly Attendance Records")
                
                # Add search functionality
                search_term = st.text_input("🔍 Search by User Name", "")
                
                display_filtered = filtered.copy()
                if search_term:
                    display_filtered = display_filtered[
                        display_filtered['User'].str.contains(search_term, case=False)
                    ]
                
                # Prepare display dataframe
                display_df = display_filtered[[
                    "User",
                    "Week",
                    "Days_Worked",
                    "Actual_Hours_Display",
                    "Target_Hours",
                    "Gap_Hours",
                    "Gap_%",
                    "Performance_Score",
                    "Compliance"
                ]].copy()
                
                display_df.columns = [
                    "Employee",
                    "Week",
                    "Days",
                    "Actual Hours",
                    "Target",
                    "Gap (h)",
                    "Gap (%)",
                    "Performance (%)",
                    "Status"
                ]
                
                # Style the dataframe
                styled_df = display_df.style.applymap(
                    lambda x: 'background-color: #d4edda' if x == '✅ Met' else 'background-color: #f8d7da',
                    subset=['Status']
                ).background_gradient(
                    subset=['Performance (%)'],
                    cmap='RdYlGn',
                    vmin=80,
                    vmax=110
                )
                
                st.dataframe(styled_df, use_container_width=True, height=500)
                
                # Summary statistics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.info(f"**Total Records:** {len(display_df)}")
                
                with col2:
                    avg_perf = display_df['Performance (%)'].mean()
                    st.info(f"**Average Performance:** {avg_perf:.1f}%")
                
                with col3:
                    compliant = len(display_df[display_df['Status'] == '✅ Met'])
                    st.info(f"**Compliant Records:** {compliant}/{len(display_df)}")
        
        else:
            st.warning("⚠️ No data matches the selected filters. Please adjust your filter criteria.")
    
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.info("Please ensure your CSV file has the correct format with 'Date/time', 'User', and 'Where' columns.")

else:
    # Welcome screen
    st.markdown("""
        <div class='upload-section'>
            <h2>👋 Welcome to Attendance Analytics Dashboard</h2>
            <p>Upload your attendance report to get started with comprehensive workforce analytics</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**📊 Key Features**\n\n✅ Real-time analytics\n\n✅ Interactive visualizations\n\n✅ Performance tracking")
    
    with col2:
        st.info("**🎯 Insights**\n\n✅ Weekly trends\n\n✅ User comparisons\n\n✅ Compliance monitoring")
    
    with col3:
        st.info("**📥 Export Options**\n\n✅ CSV format\n\n✅ Filtered reports\n\n✅ Custom date ranges")
    
    st.divider()
    
    st.subheader("📝 Required CSV Format")
    st.code("""
Date/time,User,Where
2024-01-01 09:00:00,John Doe,Office In
2024-01-01 18:00:00,John Doe,Office Out
    """, language="csv")
    
    st.caption("Ensure your CSV file contains these columns: Date/time, User, Where")

# Footer
st.divider()
st.caption("📊 Attendance Analytics Dashboard v2.0 | Built with Streamlit & Plotly | Real-time Workforce Intelligence")
