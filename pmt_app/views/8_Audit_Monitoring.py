import streamlit as st
import auth
import database
import audit
import pandas as pd
import styles
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page Config
st.set_page_config(page_title="Audit & Monitoring", layout="wide")

def audit_dashboard_page():
    auth.require_role(['admin', 'executive'])
    styles.global_css()

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0c4a6e 0%, #0ea5e9 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(12, 74, 110, 0.2);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-chart-line" style="font-size: 1.6rem;"></i>
            <div style="font-size: 1.6rem; font-weight: 700;">Audit & Monitoring Dashboard</div>
        </div>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-left: 36px;">Track user activity, file operations, and system utilization</div>
    </div>
    """, unsafe_allow_html=True)

    # Time Range Selector
    col_time1, col_time2, col_time3 = st.columns([1, 1, 3])
    with col_time1:
        time_range = st.selectbox(
            "Time Range",
            ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            key="audit_time_range"
        )
    
    # Map time range to days
    days_map = {
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 90 days": 90,
        "All time": None
    }
    days = days_map.get(time_range, 30)

    with col_time2:
        if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # =========================================================================
    # TOP METRICS
    # =========================================================================
    # Get active users
    active_users_df = audit.get_active_users(days=days or 365)
    total_users = len(active_users_df)
    
    # Get session durations
    session_df = audit.get_session_duration_summary(days=days or 365)
    total_sessions = session_df['session_count'].sum() if not session_df.empty else 0
    avg_duration = session_df['avg_duration_seconds'].mean() if not session_df.empty and 'avg_duration_seconds' in session_df.columns else 0
    
    # Get file activity
    file_activity_df = audit.get_file_activity_summary(days=days or 365)
    total_downloads = file_activity_df[file_activity_df['event_type'] == 'DOWNLOAD']['count'].sum() if not file_activity_df.empty else 0
    total_uploads = file_activity_df[file_activity_df['event_type'] == 'UPLOAD']['count'].sum() if not file_activity_df.empty else 0
    
    # Get recent activity count
    recent_df = audit.get_recent_activity(limit=1000)
    total_events = len(recent_df)

    # Display metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.metric(
            label="Active Users",
            value=total_users,
            delta=f"Unique users in {days or 'all'} days"
        )
    
    with m2:
        st.metric(
            label="Total Sessions",
            value=int(total_sessions),
            delta="Login sessions"
        )
    
    with m3:
        avg_hours = avg_duration / 3600 if avg_duration else 0
        st.metric(
            label="Avg Session Duration",
            value=f"{avg_hours:.1f}h",
            delta=f"{avg_duration:.0f} seconds"
        )
    
    with m4:
        st.metric(
            label="File Downloads",
            value=int(total_downloads),
            delta=f"Files downloaded"
        )
    
    with m5:
        st.metric(
            label="File Uploads",
            value=int(total_uploads),
            delta=f"Files uploaded"
        )

    st.divider()

    # =========================================================================
    # TABS FOR DIFFERENT VIEWS
    # =========================================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Activity Overview",
        "👥 User Activity",
        "📁 File Operations",
        "⏱️ Session Analysis",
        "📋 Audit Logs"
    ])

    # =========================================================================
    # TAB 1: ACTIVITY OVERVIEW
    # =========================================================================
    with tab1:
        st.markdown("### Activity Overview")
        
        # Get activity by category
        if not recent_df.empty:
            activity_by_category = recent_df.groupby('category').size().reset_index(name='count')
            activity_by_category = activity_by_category.sort_values('count', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Events by Category")
                fig_category = px.bar(
                    activity_by_category,
                    x='count',
                    y='category',
                    orientation='h',
                    color='count',
                    color_continuous_scale='Blues',
                    title='Activity by Category'
                )
                fig_category.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_category, use_container_width=True)
            
            with col2:
                st.markdown("#### Events by Type")
                activity_by_type = recent_df.groupby('event_type').size().reset_index(name='count')
                activity_by_type = activity_by_type.sort_values('count', ascending=False)
                
                fig_type = px.pie(
                    activity_by_type,
                    values='count',
                    names='event_type',
                    title='Activity Distribution',
                    hole=0.4
                )
                fig_type.update_layout(height=400)
                st.plotly_chart(fig_type, use_container_width=True)
            
            st.markdown("#### Activity Timeline (Last 30 Days)")
            # Get daily activity
            recent_df['date'] = pd.to_datetime(recent_df['created_at']).dt.date
            daily_activity = recent_df.groupby('date').size().reset_index(name='count')
            
            fig_timeline = px.area(
                daily_activity,
                x='date',
                y='count',
                title='Daily Activity Trend',
                labels={'date': 'Date', 'count': 'Events'}
            )
            fig_timeline.update_layout(height=300)
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("No activity data available for the selected period.")

    # =========================================================================
    # TAB 2: USER ACTIVITY
    # =========================================================================
    with tab2:
        st.markdown("### User Activity Analysis")
        
        if not active_users_df.empty:
            # Top users by activity
            st.markdown("#### Most Active Users")
            top_users = active_users_df.nlargest(10, 'total_events')[['full_name', 'username', 'role', 'total_events', 'session_count']]
            
            fig_top_users = px.bar(
                top_users,
                x='total_events',
                y='full_name',
                orientation='h',
                color='role',
                title='Top 10 Most Active Users',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_top_users.update_layout(height=400)
            st.plotly_chart(fig_top_users, use_container_width=True)
            
            st.markdown("#### User Activity Details")
            st.dataframe(
                active_users_df[['full_name', 'username', 'role', 'total_events', 'session_count', 'first_activity', 'last_activity']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No user activity data available.")

    # =========================================================================
    # TAB 3: FILE OPERATIONS
    # =========================================================================
    with tab3:
        st.markdown("### File Operations Tracking")
        
        if not file_activity_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Upload vs Download")
                fig_file_ops = px.bar(
                    file_activity_df,
                    x='event_type',
                    y='count',
                    color='event_type',
                    title='File Operations Summary',
                    labels={'event_type': 'Operation', 'count': 'Count'}
                )
                fig_file_ops.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_file_ops, use_container_width=True)
            
            with col2:
                total_bytes = file_activity_df['total_bytes'].sum() if 'total_bytes' in file_activity_df.columns else 0
                total_mb = total_bytes / (1024 * 1024) if total_bytes else 0
                st.metric("Total Data Transferred", f"{total_mb:.2f} MB")
                
                avg_size = file_activity_df['avg_size'].mean() if 'avg_size' in file_activity_df.columns else 0
                avg_mb = avg_size / (1024 * 1024) if avg_size else 0
                st.metric("Average File Size", f"{avg_mb:.2f} MB")
            
            # Get file activity by location
            file_logs = recent_df[recent_df['category'] == 'FILE']
            if not file_logs.empty and 'metadata' in file_logs.columns:
                st.markdown("#### File Activity by Location")
                # Extract location from metadata
                def extract_location(meta):
                    try:
                        import ast
                        metadata = ast.literal_eval(meta) if isinstance(meta, str) else meta
                        return metadata.get('location', 'Unknown')
                    except:
                        return 'Unknown'
                
                file_logs['location'] = file_logs['metadata'].apply(extract_location)
                location_stats = file_logs.groupby(['event_type', 'location']).size().reset_index(name='count')
                
                fig_location = px.bar(
                    location_stats,
                    x='location',
                    y='count',
                    color='event_type',
                    barmode='group',
                    title='File Operations by Location'
                )
                fig_location.update_layout(height=300)
                st.plotly_chart(fig_location, use_container_width=True)
        else:
            st.info("No file operation data available.")

    # =========================================================================
    # TAB 4: SESSION ANALYSIS
    # =========================================================================
    with tab4:
        st.markdown("### Session Duration Analysis")
        
        if not session_df.empty:
            # Convert duration to hours for better visualization
            session_df['avg_duration_hours'] = session_df['avg_duration_seconds'] / 3600
            session_df['total_duration_hours'] = session_df['total_duration_seconds'] / 3600
            
            st.markdown("#### Average Session Duration by User")
            fig_session = px.bar(
                session_df.nlargest(10, 'total_duration_hours'),
                x='full_name',
                y='avg_duration_hours',
                color='session_count',
                title='Top 10 Users by Average Session Duration',
                labels={'full_name': 'User', 'avg_duration_hours': 'Avg Duration (hours)'}
            )
            fig_session.update_layout(height=400)
            st.plotly_chart(fig_session, use_container_width=True)
            
            st.markdown("#### Session Details")
            display_df = session_df.copy()
            display_df['avg_duration_formatted'] = display_df['avg_duration_seconds'].apply(
                lambda x: f"{int(x//3600)}h {int((x%3600)//60)}m {int(x%60)}s" if pd.notna(x) else "N/A"
            )
            display_df['total_duration_formatted'] = display_df['total_duration_seconds'].apply(
                lambda x: f"{int(x//3600)}h {int((x%3600)//60)}m {int(x%60)}s" if pd.notna(x) else "N/A"
            )
            
            st.dataframe(
                display_df[['full_name', 'username', 'role', 'session_count', 
                           'avg_duration_formatted', 'total_duration_formatted', 
                           'max_duration_seconds']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "max_duration_seconds": st.column_config.NumberColumn(
                        "Max Duration (sec)",
                        format="%.0f"
                    )
                }
            )
        else:
            st.info("No session data available.")

    # =========================================================================
    # TAB 5: AUDIT LOGS
    # =========================================================================
    with tab5:
        st.markdown("### Detailed Audit Logs")
        
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_event = st.multiselect(
                "Event Type",
                options=recent_df['event_type'].unique() if not recent_df.empty else [],
                default=[]
            )
        with col_f2:
            filter_category = st.multiselect(
                "Category",
                options=recent_df['category'].unique() if not recent_df.empty else [],
                default=[]
            )
        with col_f3:
            filter_user = st.multiselect(
                "User",
                options=recent_df['full_name'].unique() if not recent_df.empty else [],
                default=[]
            )
        
        # Apply filters
        filtered_df = recent_df.copy()
        if filter_event:
            filtered_df = filtered_df[filtered_df['event_type'].isin(filter_event)]
        if filter_category:
            filtered_df = filtered_df[filtered_df['category'].isin(filter_category)]
        if filter_user:
            filtered_df = filtered_df[filtered_df['full_name'].isin(filter_user)]
        
        # Display
        st.markdown(f"#### Showing {len(filtered_df)} events")
        
        # Format for display
        display_cols = ['created_at', 'full_name', 'username', 'event_type', 'category', 'description', 'ip_address']
        available_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_cols].sort_values('created_at', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "created_at": "Timestamp",
                "full_name": "User",
                "username": "Username",
                "event_type": "Event",
                "category": "Category",
                "description": "Description",
                "ip_address": "IP Address"
            }
        )
        
        # Export option
        if not filtered_df.empty:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Export Audit Logs (CSV)",
                data=csv,
                file_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )

if __name__ == "__main__":
    audit_dashboard_page()
