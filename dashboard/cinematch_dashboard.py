"""
CineMatch - MLOps Monitoring Dashboard
Real-time monitoring of drift detection and model performance
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables
# Try local .env first (for local development)
env_path = Path(__file__).parent.parent / 'airflow' / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    # In Streamlit Cloud, use secrets
    print(f"ℹ️  Running in cloud - using Streamlit secrets")

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════ PAGE CONFIG ══════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CineMatch MLOps Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 1rem;
    }
    h2 {
        color: #ff7f0e;
        padding-top: 1rem;
    }
    .css-1d391kg {
        padding-top: 3rem;
    }
    </style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════ DATABASE CONNECTION ═════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_database_engine():
    """
    Create database connection to Neon
    Cached to avoid reconnecting on every rerun
    """
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    if not neon_conn:
        st.error("❌ NEON_CONNECTION_STRING not found in environment variables!")
        st.info("Please set your Neon connection string:\n```bash\nexport NEON_CONNECTION_STRING='your-connection-string'\n```")
        st.stop()
    
    try:
        engine = create_engine(neon_conn)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Failed to connect to database: {e}")
        st.stop()

# Get engine
engine = get_database_engine()

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════ DATA LOADING FUNCTIONS ═══════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_system_stats():
    """Load overall system statistics"""
    try:
        # Total ratings in baseline
        baseline_count = pd.read_sql("""
            SELECT COUNT(*) as count 
            FROM ratings 
            WHERE data_split = 'train'
        """, engine)
        
        # Total ratings in buffer
        buffer_count = pd.read_sql("""
            SELECT COUNT(*) as count 
            FROM ratings_buffer
        """, engine)
        
        # Number of batches
        batch_count = pd.read_sql("""
            SELECT COUNT(DISTINCT batch_id) as count 
            FROM ratings_buffer
        """, engine)
        
        # Latest batch
        latest_batch = pd.read_sql("""
            SELECT batch_id, ingested_at 
            FROM ratings_buffer 
            WHERE ingested_at IS NOT NULL
            ORDER BY ingested_at DESC 
            LIMIT 1
        """, engine)
        
        # Convert latest_ingestion to datetime if it exists
        latest_ingestion = None
        if len(latest_batch) > 0 and latest_batch['ingested_at'][0]:
            try:
                # Try to parse the datetime string
                latest_ingestion = pd.to_datetime(latest_batch['ingested_at'][0])
            except:
                latest_ingestion = latest_batch['ingested_at'][0]  # Keep as string if parsing fails
        
        return {
            'baseline_count': baseline_count['count'][0] if len(baseline_count) > 0 else 0,
            'buffer_count': buffer_count['count'][0] if len(buffer_count) > 0 else 0,
            'batch_count': batch_count['count'][0] if len(batch_count) > 0 else 0,
            'latest_batch': latest_batch['batch_id'][0] if len(latest_batch) > 0 else 'N/A',
            'latest_ingestion': latest_ingestion
        }
    except Exception as e:
        st.error(f"Error loading system stats: {e}")
        return None

@st.cache_data(ttl=60)
def load_drift_alerts():
    """Load drift alerts from database"""
    try:
        df = pd.read_sql("""
            SELECT 
                id,
                alert_date,
                feature_name,
                drift_score,
                threshold,
                alert_triggered,
                notes
            FROM drift_alerts
            ORDER BY alert_date DESC
        """, engine)
        return df
    except Exception as e:
        st.error(f"Error loading drift alerts: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_buffer_batches():
    """Load buffer batch statistics"""
    try:
        df = pd.read_sql("""
            SELECT 
                batch_id,
                COUNT(*) as ratings_count,
                AVG(rating) as avg_rating,
                STDDEV(rating) as std_rating,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                MIN(ingested_at) as ingested_at
            FROM ratings_buffer
            GROUP BY batch_id
            ORDER BY batch_id
        """, engine)
        
        # Convert ingested_at to datetime if it exists
        if 'ingested_at' in df.columns:
            df['ingested_at'] = pd.to_datetime(df['ingested_at'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading buffer batches: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_retraining_decisions():
    """Load retraining decision log"""
    try:
        df = pd.read_sql("""
            SELECT 
                id,
                decision_date,
                decision,
                reason,
                buffer_size,
                drift_score,
                notes
            FROM retraining_decisions
            ORDER BY decision_date DESC
        """, engine)
        return df
    except Exception as e:
        # Table might not exist yet
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_rating_distributions():
    """Load rating distributions for baseline vs buffer"""
    try:
        # Baseline distribution
        baseline = pd.read_sql("""
            SELECT rating, COUNT(*) as count
            FROM ratings
            WHERE data_split = 'train'
            GROUP BY rating
            ORDER BY rating
        """, engine)
        baseline['source'] = 'Baseline'
        
        # Buffer distribution
        buffer = pd.read_sql("""
            SELECT rating, COUNT(*) as count
            FROM ratings_buffer
            GROUP BY rating
            ORDER BY rating
        """, engine)
        buffer['source'] = 'Buffer'
        
        # Combine
        df = pd.concat([baseline, buffer], ignore_index=True)
        return df
    except Exception as e:
        st.error(f"Error loading distributions: {e}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════ SIDEBAR NAVIGATION ═══════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

st.sidebar.title("🎬 CineMatch")
st.sidebar.markdown("### MLOps Monitoring Dashboard")
st.sidebar.markdown("---")

# Page selection
page = st.sidebar.radio(
    "Navigation",
    ["📊 Overview", "🔍 Drift Monitoring", "⚙️ Pipeline Status"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Quick Stats")

# Load stats for sidebar
stats = load_system_stats()
if stats:
    st.sidebar.metric("Total Ratings", f"{stats['baseline_count'] + stats['buffer_count']:,}")
    st.sidebar.metric("Buffer Batches", stats['batch_count'])
    st.sidebar.metric("Latest Batch", stats['latest_batch'])

# Refresh button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Team:** Agnès, Julien, Matéo")
st.sidebar.markdown("**Bootcamp:** Jedha - Jan 2026")

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════ PAGE 1: OVERVIEW ═════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

if page == "📊 Overview":
    st.title("📊 System Overview")
    st.markdown("Real-time monitoring of the CineMatch recommendation system")
    
    # Load data
    stats = load_system_stats()
    df_drift = load_drift_alerts()
    df_batches = load_buffer_batches()
    
    if stats is None:
        st.error("Failed to load system statistics")
        st.stop()
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Key Metrics Row
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Baseline Ratings",
            f"{stats['baseline_count']:,}",
            help="Training data size"
        )
    
    with col2:
        st.metric(
            "Buffer Ratings",
            f"{stats['buffer_count']:,}",
            help="New data accumulated"
        )
    
    with col3:
        total_alerts = len(df_drift[df_drift['alert_triggered'] == True]) if len(df_drift) > 0 else 0
        st.metric(
            "Drift Alerts",
            total_alerts,
            help="Number of drift detections",
            delta="Critical" if total_alerts > 0 else None
        )
    
    with col4:
        st.metric(
            "Batches Ingested",
            stats['batch_count'],
            help="Weekly batch count"
        )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # System Status
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 🚦 System Status")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Check for recent drift
        recent_drift = df_drift[df_drift['alert_triggered'] == True].head(1) if len(df_drift) > 0 else pd.DataFrame()
        
        if len(recent_drift) > 0:
            st.error("🚨 **DRIFT DETECTED!**")
            st.markdown(f"""
            - **Feature:** {recent_drift.iloc[0]['feature_name']}
            - **Drift Score:** {recent_drift.iloc[0]['drift_score']:.4f}
            - **Threshold:** {recent_drift.iloc[0]['threshold']:.4f}
            - **Date:** {recent_drift.iloc[0]['alert_date'].strftime('%Y-%m-%d %H:%M')}
            """)
            st.warning("⚠️ Retraining recommended")
        else:
            st.success("✅ **System Healthy** - No drift detected")
            st.markdown("All monitoring metrics within acceptable thresholds")
    
    with col2:
        st.markdown("**Last Update:**")
        if stats['latest_ingestion']:
            try:
                # If it's a datetime object, use strftime
                if hasattr(stats['latest_ingestion'], 'strftime'):
                    st.info(f"🕐 {stats['latest_ingestion'].strftime('%Y-%m-%d %H:%M')}")
                else:
                    # If it's a string, display as is
                    st.info(f"🕐 {stats['latest_ingestion']}")
            except:
                st.info(f"🕐 {stats['latest_ingestion']}")
        else:
            st.info("🕐 N/A")
        
        st.markdown("**Latest Batch:**")
        st.info(f"📦 {stats['latest_batch']}")
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Recent Activity
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 📋 Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Latest Drift Checks")
        if len(df_drift) > 0:
            recent_checks = df_drift.head(5).copy()
            recent_checks['Status'] = recent_checks['alert_triggered'].apply(
                lambda x: '🚨 ALERT' if x else '✅ OK'
            )
            recent_checks['Date'] = recent_checks['alert_date'].dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(
                recent_checks[['Date', 'feature_name', 'drift_score', 'Status']],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No drift checks recorded yet")
    
    with col2:
        st.markdown("#### Buffer Batches")
        if len(df_batches) > 0:
            batch_summary = df_batches.copy()
            batch_summary['avg_rating'] = batch_summary['avg_rating'].round(2)
            batch_summary['ratings_count'] = batch_summary['ratings_count'].apply(lambda x: f"{x:,}")
            
            st.dataframe(
                batch_summary[['batch_id', 'ratings_count', 'avg_rating']],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No batches in buffer yet")
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Rating Distribution Comparison
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 📊 Rating Distribution: Baseline vs Buffer")
    
    df_dist = load_rating_distributions()
    
    if len(df_dist) > 0:
        fig = px.bar(
            df_dist,
            x='rating',
            y='count',
            color='source',
            barmode='group',
            title='Rating Distribution Comparison',
            labels={'rating': 'Rating', 'count': 'Count', 'source': 'Data Source'},
            color_discrete_map={'Baseline': '#1f77b4', 'Buffer': '#ff7f0e'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No distribution data available")

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════ PAGE 2: DRIFT MONITORING ═════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

elif page == "🔍 Drift Monitoring":
    st.title("🔍 Drift Monitoring")
    st.markdown("Statistical detection of data distribution changes")
    
    # Load drift data
    df_drift = load_drift_alerts()
    
    if len(df_drift) == 0:
        st.warning("⚠️ No drift monitoring data available yet")
        st.info("Run the `drift_monitoring` DAG to generate drift detection data")
        st.stop()
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Summary Cards
    # ─────────────────────────────────────────────────────────────────────────────────
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_checks = len(df_drift)
    triggered = len(df_drift[df_drift['alert_triggered'] == True])
    max_drift = df_drift['drift_score'].max()
    latest_check = df_drift['alert_date'].max()
    
    with col1:
        st.metric("Total Checks", total_checks)
    
    with col2:
        st.metric("Alerts Triggered", triggered, delta="Critical" if triggered > 0 else "Normal")
    
    with col3:
        st.metric("Max Drift Score", f"{max_drift:.4f}")
    
    with col4:
        st.metric("Latest Check", latest_check.strftime('%m/%d'))
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Drift Over Time Chart
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 📈 Drift Scores Over Time")
    
    # Create line chart for each feature
    fig = go.Figure()
    
    for feature in df_drift['feature_name'].unique():
        feature_data = df_drift[df_drift['feature_name'] == feature].copy()
        feature_data = feature_data.sort_values('alert_date')
        
        fig.add_trace(go.Scatter(
            x=feature_data['alert_date'],
            y=feature_data['drift_score'],
            name=feature,
            mode='lines+markers',
            line=dict(width=2),
            marker=dict(size=8)
        ))
    
    # Add threshold line (using first threshold value)
    threshold = df_drift['threshold'].iloc[0]
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Threshold: {threshold}",
        annotation_position="right"
    )
    
    fig.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title="Drift Score",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Feature-wise Drift Analysis
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 🎯 Feature-wise Drift Analysis")
    
    # Get latest values for each feature
    latest_by_feature = df_drift.sort_values('alert_date').groupby('feature_name').last().reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart of latest drift scores
        fig = px.bar(
            latest_by_feature,
            x='feature_name',
            y='drift_score',
            color='alert_triggered',
            title='Latest Drift Scores by Feature',
            labels={'feature_name': 'Feature', 'drift_score': 'Drift Score'},
            color_discrete_map={True: '#ff4444', False: '#44ff44'}
        )
        fig.add_hline(y=threshold, line_dash="dash", line_color="red")
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Status indicators
        st.markdown("#### Current Status")
        for _, row in latest_by_feature.iterrows():
            if row['alert_triggered']:
                st.error(f"🚨 **{row['feature_name']}**")
                st.markdown(f"Score: {row['drift_score']:.4f} (Threshold: {row['threshold']:.4f})")
            else:
                st.success(f"✅ **{row['feature_name']}**")
                st.markdown(f"Score: {row['drift_score']:.4f} (Threshold: {row['threshold']:.4f})")
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Detailed Alerts Table
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 📋 Detailed Drift Alerts Log")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_all = st.checkbox("Show all checks", value=False)
    
    with col2:
        feature_filter = st.multiselect(
            "Filter by feature",
            options=df_drift['feature_name'].unique(),
            default=df_drift['feature_name'].unique()
        )
    
    # Filter data
    if show_all:
        filtered = df_drift[df_drift['feature_name'].isin(feature_filter)]
    else:
        filtered = df_drift[
            (df_drift['alert_triggered'] == True) &
            (df_drift['feature_name'].isin(feature_filter))
        ]
    
    # Format for display
    display_df = filtered.copy()
    display_df['alert_date'] = display_df['alert_date'].dt.strftime('%Y-%m-%d %H:%M')
    display_df['drift_score'] = display_df['drift_score'].round(4)
    display_df['threshold'] = display_df['threshold'].round(4)
    display_df['Status'] = display_df['alert_triggered'].apply(lambda x: '🚨 ALERT' if x else '✅ OK')
    
    st.dataframe(
        display_df[['alert_date', 'feature_name', 'drift_score', 'threshold', 'Status', 'notes']],
        hide_index=True,
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Drift Log (CSV)",
        data=csv,
        file_name=f"drift_log_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════ PAGE 3: PIPELINE STATUS ══════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

elif page == "⚙️ Pipeline Status":
    st.title("⚙️ Pipeline Status")
    st.markdown("MLOps pipeline execution and retraining decisions")
    
    # Load data
    df_decisions = load_retraining_decisions()
    df_batches = load_buffer_batches()
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Pipeline Overview
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 🔄 Pipeline Architecture")
    
    st.markdown("""
    ```
    ┌─────────────────────┐
    │ Buffer Ingestion    │  ← Weekly batch loading
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │ Batch Predictions   │  ← API calls + Model drift detection
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │ Drift Monitoring    │  ← Statistical data drift detection
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │ Trigger Retraining  │  ← Decision logic (mock)
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │ Model Retraining    │  ← (Future: GitHub Actions)
    └─────────────────────┘
    ```
    """)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Retraining Decisions
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 🤖 Retraining Decision Log")
    
    if len(df_decisions) > 0:
        col1, col2, col3 = st.columns(3)
        
        total_decisions = len(df_decisions)
        triggered = len(df_decisions[df_decisions['decision'].str.contains('trigger', case=False, na=False)])
        no_action = len(df_decisions[df_decisions['decision'] == 'no_action'])
        
        with col1:
            st.metric("Total Decisions", total_decisions)
        
        with col2:
            st.metric("Retraining Triggered", triggered)
        
        with col3:
            st.metric("No Action Taken", no_action)
        
        # Timeline chart
        st.markdown("#### Decision Timeline")
        
        # Handle NaN values in drift_score for plotting
        plot_df = df_decisions.copy()
        # Fill NaN drift scores with a small default value for plotting
        plot_df['drift_score_plot'] = plot_df['drift_score'].fillna(0.001)
        
        fig = px.scatter(
            plot_df,
            x='decision_date',
            y='buffer_size',
            color='decision',
            size='drift_score_plot',
            hover_data=['reason', 'notes'],
            title='Retraining Decisions Over Time',
            labels={
                'decision_date': 'Date',
                'buffer_size': 'Buffer Size',
                'decision': 'Decision',
                'drift_score_plot': 'Drift Score'
            }
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.markdown("#### Decision Details")
        
        display_df = df_decisions.copy()
        display_df['decision_date'] = display_df['decision_date'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['buffer_size'] = display_df['buffer_size'].apply(lambda x: f"{x:,}" if pd.notna(x) else "N/A")
        display_df['drift_score'] = display_df['drift_score'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")
        
        st.dataframe(
            display_df[['decision_date', 'decision', 'reason', 'buffer_size', 'drift_score', 'notes']],
            hide_index=True,
            use_container_width=True,
            height=300
        )
    else:
        st.info("ℹ️ No retraining decisions logged yet")
        st.markdown("Run the `trigger_retraining_dag` to log decisions")
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # Batch Processing Timeline
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 📦 Batch Processing Timeline")
    
    if len(df_batches) > 0:
        # Create timeline chart
        fig = go.Figure()
        
        for idx, row in df_batches.iterrows():
            fig.add_trace(go.Bar(
                name=row['batch_id'],
                x=[row['ratings_count']],
                y=[row['batch_id']],
                orientation='h',
                text=f"{row['ratings_count']:,} ratings",
                textposition='auto',
                hovertemplate=(
                    f"<b>{row['batch_id']}</b><br>" +
                    f"Ratings: {row['ratings_count']:,}<br>" +
                    f"Avg Rating: {row['avg_rating']:.2f}<br>" +
                    f"Ingested: {row['ingested_at'].strftime('%Y-%m-%d') if pd.notna(row['ingested_at']) and hasattr(row['ingested_at'], 'strftime') else str(row['ingested_at']) if pd.notna(row['ingested_at']) else 'N/A'}<br>" +
                    "<extra></extra>"
                )
            ))
        
        fig.update_layout(
            height=max(300, len(df_batches) * 50),
            xaxis_title="Number of Ratings",
            yaxis_title="Batch ID",
            showlegend=False,
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Batch statistics table
        st.markdown("#### Batch Statistics")
        
        display_df = df_batches.copy()
        display_df['ratings_count'] = display_df['ratings_count'].apply(lambda x: f"{x:,}")
        display_df['avg_rating'] = display_df['avg_rating'].round(2)
        display_df['std_rating'] = display_df['std_rating'].round(2)
        # Handle ingested_at whether it's datetime or string
        display_df['ingested_at'] = display_df['ingested_at'].apply(
            lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notna(x) and hasattr(x, 'strftime') 
            else str(x) if pd.notna(x) else 'N/A'
        )
        
        st.dataframe(
            display_df[['batch_id', 'ratings_count', 'avg_rating', 'std_rating', 'ingested_at']],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("ℹ️ No batches processed yet")
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # System Health
    # ─────────────────────────────────────────────────────────────────────────────────
    
    st.markdown("### 🏥 System Health")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Database Connection")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM ratings"))
                count = result.fetchone()[0]
            st.success(f"✅ Connected - {count:,} baseline ratings")
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
    
    with col2:
        st.markdown("#### Data Freshness")
        stats = load_system_stats()
        if stats and stats['latest_ingestion']:
            age = datetime.now() - stats['latest_ingestion'].replace(tzinfo=None)
            if age.total_seconds() < 3600:  # Less than 1 hour
                st.success(f"✅ Fresh data ({age.seconds // 60} min ago)")
            elif age.total_seconds() < 86400:  # Less than 1 day
                st.warning(f"⚠️ Data is {age.seconds // 3600} hours old")
            else:
                st.error(f"❌ Data is {age.days} days old")
        else:
            st.info("ℹ️ No ingestion data available")

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════ FOOTER ═══════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>CineMatch MLOps Dashboard</strong> | Jedha Bootcamp Final Project | January 2026</p>
    <p>Team: Agnès (Data Pipeline) • Julien (Model Training) • Matéo (API & Testing)</p>
</div>
""", unsafe_allow_html=True)
