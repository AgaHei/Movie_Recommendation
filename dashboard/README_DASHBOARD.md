# CineMatch Dashboard - Setup Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
# Create virtual environment (optional but recommended)
python -m venv dashboard_env
source dashboard_env/bin/activate  # On Windows: dashboard_env\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Configure Database Connection

**✅ No manual setup needed!** 

The dashboard automatically loads your database connection from the `.env` file in the `airflow` folder:

```
cinematch/
├── airflow/
│   └── .env                 # Your connection string is here
├── dashboard/
│   └── cinematch_dashboard.py   # Automatically finds ../airflow/.env
```

The connection string (`NEON_CONNECTION_STRING`) is automatically loaded from:
`../airflow/.env`

**Note:** Make sure your `.env` file in the airflow folder contains:
```
NEON_CONNECTION_STRING=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
```

### Step 3: Run Dashboard

```bash
streamlit run cinematch_dashboard.py
```

**Dashboard will open automatically in your browser at http://localhost:8501**

---

## 📊 Dashboard Features

### Page 1: Overview
- System metrics (baseline, buffer, alerts)
- System status (drift detected or healthy)
- Recent activity summary
- Rating distribution comparison

### Page 2: Drift Monitoring
- Drift scores over time (line chart)
- Feature-wise analysis
- Detailed alerts log with filtering
- CSV export

### Page 3: Pipeline Status
- Pipeline architecture diagram
- Retraining decision log
- Batch processing timeline
- System health indicators

---

## 🎬 For Presentation

### Demo Tips

1. **Start with Overview page**
   - Show system metrics
   - Point out drift alert

2. **Navigate to Drift Monitoring**
   - Show drift chart over time
   - Explain KS test threshold
   - Filter to show triggered alerts

3. **Show Pipeline Status**
   - Walk through architecture
   - Show retraining decisions
   - Demonstrate system health

### Talking Points

> "This dashboard provides real-time monitoring of our MLOps pipeline. It connects directly to our Neon database and visualizes the drift detection, batch processing, and retraining decisions we've automated."

> "Here you can see we detected drift in week 7 - the KS statistic exceeded our 0.05 threshold. This automatically triggered our retraining pipeline."

> "All decisions are logged and auditable - a key requirement for production ML systems."

---

## 🐛 Troubleshooting

### Dashboard won't start

**Error: "NEON_CONNECTION_STRING not found"**
```bash
# Make sure environment variable is set
echo $NEON_CONNECTION_STRING  # Should show your connection string

# If empty, set it again
export NEON_CONNECTION_STRING="your-string"
```

**Error: "Failed to connect to database"**
- Check your connection string is correct
- Verify Neon database is accessible
- Check your IP is whitelisted in Neon

### No data showing

**"No drift monitoring data available"**
- Run your `drift_monitoring` DAG in Airflow first
- Check `drift_alerts` table has data

**"No retraining decisions logged"**
- Run your `trigger_retraining_dag` in Airflow
- Check `retraining_decisions` table exists

### Charts not rendering

```bash
# Reinstall plotly
pip install --upgrade plotly
```

---

## 🚀 Deployment (Optional - Tomorrow)

### Deploy to Streamlit Cloud (Free!)

1. **Push to GitHub**
   ```bash
   git add cinematch_dashboard.py requirements.txt
   git commit -m "Add MLOps monitoring dashboard"
   git push
   ```

2. **Go to https://share.streamlit.io**

3. **Click "New app"**

4. **Configure:**
   - Repository: Your GitHub repo
   - Branch: main
   - Main file: cinematch_dashboard.py

5. **Add Secrets:**
   - Click "Advanced settings"
   - Add secrets:
     ```toml
     NEON_CONNECTION_STRING = "postgresql://..."
     ```

6. **Deploy!**
   - Takes ~2 minutes
   - Get public URL to share

---

## 🎨 Customization

### Change Colors

Edit the custom CSS section (line ~30):
```python
st.markdown("""
    <style>
    h1 {
        color: #1f77b4;  # Change header color
    }
    </style>
""", unsafe_allow_html=True)
```

### Add Logo

```python
# Add after page config
st.sidebar.image("logo.png", use_column_width=True)
```

### Change Refresh Rate

```python
# Line ~89 - change ttl (time to live in seconds)
@st.cache_data(ttl=60)  # Change to 30, 120, etc.
```

---

## 📝 File Structure

```
your-project/
├── cinematch_dashboard.py   # Main dashboard
├── requirements.txt          # Dependencies
└── README_DASHBOARD.md       # This file
```

---

## 💡 Tips for Demo Day

### Before Presentation

- [ ] Test dashboard runs without errors
- [ ] Verify all 3 pages load
- [ ] Check data is up-to-date
- [ ] Take screenshots as backup
- [ ] Practice navigation

### During Presentation

- [ ] Close unnecessary browser tabs
- [ ] Zoom browser to 110-125% (visibility)
- [ ] Use sidebar navigation smoothly
- [ ] Highlight key metrics with cursor
- [ ] Explain what each chart shows

### Backup Plan

If dashboard fails:
1. Show screenshots
2. Walk through code briefly
3. Explain architecture
4. Still impressive!

---

## 🎓 What This Demonstrates

**Technical Skills:**
- ✅ Full-stack development (frontend + backend)
- ✅ Database integration
- ✅ Data visualization
- ✅ Real-time monitoring
- ✅ Production-ready tools

**MLOps Best Practices:**
- ✅ Observability (monitoring drift)
- ✅ Audit trails (decision logging)
- ✅ System health checks
- ✅ Data quality monitoring

**Business Value:**
- ✅ Actionable insights
- ✅ Early warning system
- ✅ Decision support
- ✅ Operational transparency

---

## 📚 Resources

- **Streamlit Docs:** https://docs.streamlit.io
- **Plotly Charts:** https://plotly.com/python/
- **Neon Docs:** https://neon.tech/docs

---

**Questions? Issues?** Check troubleshooting section above!

**Good luck with your presentation! 🚀🎬**
