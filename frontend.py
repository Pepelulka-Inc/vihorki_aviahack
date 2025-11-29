import streamlit as st
import requests
import json
import time
from datetime import datetime

# Streamlit page configuration
st.set_page_config(
    page_title="Metrics Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

def fetch_analysis_result():
    """Fetch the latest analysis result from the backend"""
    try:
        response = requests.get(
            "http://localhost:9002/api/v1/analyze-metrics",  # This would be the actual endpoint
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def display_metrics_comparison(release1, release2):
    """Display side-by-side comparison of two releases"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"Release: {release1['release_info']['version']}")
        st.metric("Total Visits", release1['release_info']['total_visits'])
        st.metric("Total Hits", release1['release_info']['total_hits'])
        st.metric("Unique Clients", release1['release_info']['unique_clients'])
        
        # Aggregate metrics
        visits1 = release1['aggregate_metrics']['visits']
        st.write("**Visits Metrics:**")
        st.metric("Avg. Page Views", f"{visits1['avg_page_views']:.2f}")
        st.metric("Avg. Duration (sec)", f"{visits1['avg_duration_sec']:.2f}")
        
    with col2:
        st.subheader(f"Release: {release2['release_info']['version']}")
        st.metric("Total Visits", release2['release_info']['total_visits'])
        st.metric("Total Hits", release2['release_info']['total_hits'])
        st.metric("Unique Clients", release2['release_info']['unique_clients'])
        
        # Aggregate metrics
        visits2 = release2['aggregate_metrics']['visits']
        st.write("**Visits Metrics:**")
        st.metric("Avg. Page Views", f"{visits2['avg_page_views']:.2f}")
        st.metric("Avg. Duration (sec)", f"{visits2['avg_duration_sec']:.2f}")

def display_improvements(release1, release2):
    """Display improvements between releases"""
    visits1 = release1['aggregate_metrics']['visits']
    visits2 = release2['aggregate_metrics']['visits']
    
    st.subheader("Improvements from v1.0.0 to v1.1.0")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        improvement = ((visits2['avg_page_views'] - visits1['avg_page_views']) / visits1['avg_page_views']) * 100
        st.metric(
            "Avg. Page Views Improvement", 
            f"{visits2['avg_page_views']:.2f}", 
            f"{improvement:+.2f}%"
        )
    
    with col2:
        improvement = ((visits2['avg_duration_sec'] - visits1['avg_duration_sec']) / visits1['avg_duration_sec']) * 100
        st.metric(
            "Avg. Duration Improvement (sec)", 
            f"{visits2['avg_duration_sec']:.2f}", 
            f"{improvement:+.2f}%"
        )
    
    with col3:
        visits_improvement = ((release2['release_info']['total_visits'] - release1['release_info']['total_visits']) / release1['release_info']['total_visits']) * 100
        st.metric(
            "Total Visits Improvement", 
            release2['release_info']['total_visits'], 
            f"{visits_improvement:+.2f}%"
        )

def display_session_distributions(release1, release2):
    """Display session distribution charts"""
    import pandas as pd
    import plotly.express as px
    
    st.subheader("Session Distribution by Page Views")
    
    # Prepare data for page views distribution
    pv_data1 = []
    for item in release1['session_distribution']['by_page_views']:
        label = f"{item['range_min']}-{item['range_max'] if item['range_max'] else '+'}"
        pv_data1.append({"Range": label, "Count": item['count'], "Release": release1['release_info']['version']})
    
    pv_data2 = []
    for item in release2['session_distribution']['by_page_views']:
        label = f"{item['range_min']}-{item['range_max'] if item['range_max'] else '+'}"
        pv_data2.append({"Range": label, "Count": item['count'], "Release": release2['release_info']['version']})
    
    df_pv = pd.DataFrame(pv_data1 + pv_data2)
    
    fig_pv = px.bar(
        df_pv, 
        x='Range', 
        y='Count', 
        color='Release',
        barmode='group',
        title='Page Views Distribution'
    )
    st.plotly_chart(fig_pv, use_container_width=True)
    
    # Duration distribution
    st.subheader("Session Distribution by Duration")
    
    dur_data1 = []
    for item in release1['session_distribution']['by_duration_sec']:
        label = f"{item['range_min']}-{item['range_max'] if item['range_max'] else '+'} sec"
        dur_data1.append({"Range": label, "Count": item['count'], "Release": release1['release_info']['version']})
    
    dur_data2 = []
    for item in release2['session_distribution']['by_duration_sec']:
        label = f"{item['range_min']}-{item['range_max'] if item['range_max'] else '+'} sec"
        dur_data2.append({"Range": label, "Count": item['count'], "Release": release2['release_info']['version']})
    
    df_dur = pd.DataFrame(dur_data1 + dur_data2)
    
    fig_dur = px.bar(
        df_dur, 
        x='Range', 
        y='Count', 
        color='Release',
        barmode='group',
        title='Duration Distribution'
    )
    st.plotly_chart(fig_dur, use_container_width=True)

def display_device_breakdown(release1, release2):
    """Display device breakdown"""
    import pandas as pd
    import plotly.express as px
    
    st.subheader("Device Category Breakdown")
    
    # Prepare data
    device_data = []
    
    for item in release1['device_breakdown']['by_category']:
        device_data.append({
            "Release": release1['release_info']['version'],
            "Device": item['segment_value'],
            "Visits": item['visits'],
            "Percentage": item['percentage']
        })
    
    for item in release2['device_breakdown']['by_category']:
        device_data.append({
            "Release": release2['release_info']['version'],
            "Device": item['segment_value'],
            "Visits": item['visits'],
            "Percentage": item['percentage']
        })
    
    df_device = pd.DataFrame(device_data)
    
    fig_device = px.bar(
        df_device,
        x='Device',
        y='Visits',
        color='Release',
        barmode='group',
        title='Visits by Device Category'
    )
    st.plotly_chart(fig_device, use_container_width=True)

def display_top_pages(release1, release2):
    """Display top pages metrics"""
    import pandas as pd
    
    st.subheader("Top Pages Comparison")
    
    # Prepare data
    pages_data = []
    
    for page in release1['page_metrics']:
        pages_data.append({
            "URL": page['url'],
            "Title": page['title'],
            "Visits as Entry": page['visits_as_entry'],
            "Visits as Exit": page['visits_as_exit'],
            "Total Hits": page['total_hits'],
            "Unique Visitors": page['unique_visitors'],
            "Release": release1['release_info']['version']
        })
    
    for page in release2['page_metrics']:
        pages_data.append({
            "URL": page['url'],
            "Title": page['title'],
            "Visits as Entry": page['visits_as_entry'],
            "Visits as Exit": page['visits_as_exit'],
            "Total Hits": page['total_hits'],
            "Unique Visitors": page['unique_visitors'],
            "Release": release2['release_info']['version']
        })
    
    df_pages = pd.DataFrame(pages_data)
    
    st.dataframe(df_pages, use_container_width=True)

def display_geographic_distribution(release1, release2):
    """Display geographic distribution"""
    import pandas as pd
    
    st.subheader("Top Cities Comparison")
    
    # Prepare data
    geo_data = []
    
    for city in release1['geographic_distribution']['top_cities']:
        geo_data.append({
            "City": city['segment_value'],
            "Visits": city['visits'],
            "Percentage": city['percentage'],
            "Avg. Page Views": city['avg_page_views'],
            "Avg. Duration": city['avg_duration_sec'],
            "Single Page Visits": city['single_page_visits'],
            "Release": release1['release_info']['version']
        })
    
    for city in release2['geographic_distribution']['top_cities']:
        geo_data.append({
            "City": city['segment_value'],
            "Visits": city['visits'],
            "Percentage": city['percentage'],
            "Avg. Page Views": city['avg_page_views'],
            "Avg. Duration": city['avg_duration_sec'],
            "Single Page Visits": city['single_page_visits'],
            "Release": release2['release_info']['version']
        })
    
    df_geo = pd.DataFrame(geo_data)
    
    st.dataframe(df_geo, use_container_width=True)

# Main app
st.title("📊 Metrics Analysis Dashboard")

# Auto-refresh button
if st.button("🔄 Refresh Data"):
    st.session_state.analysis_result = None
    st.session_state.last_update = None

# Try to get analysis result
if st.session_state.analysis_result is None:
    # Simulate the result since we can't make the actual POST request
    # In a real scenario, you would fetch this from your backend
    simulated_result = {
        "releases": [
            {
                "release_info": {
                    "version": "v1.0.0",
                    "data_period": {
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-07T23:59:59Z"
                    },
                    "total_visits": 10000,
                    "total_hits": 50000,
                    "unique_clients": 8000
                },
                "aggregate_metrics": {
                    "visits": {
                        "total_count": 10000,
                        "new_users": 3000,
                        "returning_users": 7000,
                        "avg_page_views": 5.2,
                        "median_page_views": 4,
                        "avg_duration_sec": 180,
                        "median_duration_sec": 120,
                        "total_duration_sec": 1800000
                    },
                    "page_views": {
                        "total_count": 50000,
                        "unique_urls": 250
                    }
                },
                "session_distribution": {
                    "by_page_views": [
                        {"range_min": 1, "range_max": 1, "count": 2000, "percentage": 20.0},
                        {"range_min": 2, "range_max": 5, "count": 5000, "percentage": 50.0},
                        {"range_min": 6, "range_max": 10, "count": 2000, "percentage": 20.0},
                        {"range_min": 11, "range_max": None, "count": 1000, "percentage": 10.0}
                    ],
                    "by_duration_sec": [
                        {"range_min": 0, "range_max": 30, "count": 1000, "percentage": 10.0},
                        {"range_min": 31, "range_max": 120, "count": 4000, "percentage": 40.0},
                        {"range_min": 121, "range_max": 300, "count": 3000, "percentage": 30.0},
                        {"range_min": 301, "range_max": None, "count": 2000, "percentage": 20.0}
                    ]
                },
                "device_breakdown": {
                    "by_category": [
                        {"device_category": 1, "segment_value": "Desktop", "visits": 6000, "percentage": 60.0, "avg_page_views": 5.5, "avg_duration_sec": 200, "single_page_visits": 1000}
                    ],
                    "by_os": [
                        {"segment_value": "Windows", "visits": 4000, "percentage": 40.0, "avg_page_views": 5.3, "avg_duration_sec": 190, "single_page_visits": 700}
                    ],
                    "by_browser": [
                        {"segment_value": "Chrome", "visits": 5000, "percentage": 50.0, "avg_page_views": 5.1, "avg_duration_sec": 175, "single_page_visits": 1000}
                    ],
                    "by_screen_orientation": [
                        {"segment_value": "landscape", "visits": 7000, "percentage": 70.0, "avg_page_views": 5.3, "avg_duration_sec": 185, "single_page_visits": 1300}
                    ]
                },
                "traffic_sources": {
                    "by_search_engine": [
                        {"segment_value": "google", "visits": 5000, "percentage": 50.0, "avg_page_views": 5.2, "avg_duration_sec": 180, "single_page_visits": 1000}
                    ]
                },
                "geographic_distribution": {
                    "top_cities": [
                        {"segment_value": "Moscow", "visits": 3000, "percentage": 30.0, "avg_page_views": 5.5, "avg_duration_sec": 200, "single_page_visits": 500}
                    ]
                },
                "page_metrics": [
                    {"url": "/home", "title": "Home", "visits_as_entry": 5000, "visits_as_exit": 2000, "total_hits": 8000, "unique_visitors": 4500, "visits_with_single_page": 1000, "subsequent_page_diversity": 15}
                ],
                "navigation_patterns": {
                    "reverse_navigation": {"visits_with_reverse_nav": 2000, "percentage": 20.0, "total_reverse_transitions": 3500},
                    "common_transitions": [
                        {"from_url": "/home", "to_url": "/products", "transition_count": 3000}
                    ],
                    "loop_patterns": [
                        {"sequence": ["/products", "/detail", "/products"], "occurrences": 500}
                    ]
                },
                "funnel_metrics": {
                    "application_funnel": [
                        {"step": 1, "url": "/home", "visits_entered": 10000, "visits_completed": 7000}
                    ]
                },
                "session_complexity_metrics": {
                    "high_interaction_sessions": {"sessions_with_10plus_pages": 1000, "percentage": 10.0, "avg_pages": 15.5, "avg_duration_sec": 450, "avg_unique_urls": 12.3},
                    "url_revisit_patterns": {"sessions_with_url_revisits": 2500, "percentage": 25.0, "avg_revisits_per_session": 2.8, "avg_unique_urls_revisited": 1.9}
                }
            },
            {
                "release_info": {
                    "version": "v1.1.0",
                    "data_period": {
                        "start": "2024-01-24T00:00:00Z",
                        "end": "2024-01-31T23:59:59Z"
                    },
                    "total_visits": 11500,
                    "total_hits": 57500,
                    "unique_clients": 9200
                },
                "aggregate_metrics": {
                    "visits": {
                        "total_count": 11500,
                        "new_users": 3450,
                        "returning_users": 8050,
                        "avg_page_views": 5.98,
                        "median_page_views": 5,
                        "avg_duration_sec": 207,
                        "median_duration_sec": 138,
                        "total_duration_sec": 2070000
                    },
                    "page_views": {
                        "total_count": 57500,
                        "unique_urls": 288
                    }
                },
                "session_distribution": {
                    "by_page_views": [
                        {"range_min": 1, "range_max": 1, "count": 1800, "percentage": 15.7},
                        {"range_min": 2, "range_max": 5, "count": 5500, "percentage": 47.8},
                        {"range_min": 6, "range_max": 10, "count": 2700, "percentage": 23.5},
                        {"range_min": 11, "range_max": None, "count": 1500, "percentage": 13.0}
                    ],
                    "by_duration_sec": [
                        {"range_min": 0, "range_max": 30, "count": 900, "percentage": 7.8},
                        {"range_min": 31, "range_max": 120, "count": 4200, "percentage": 36.5},
                        {"range_min": 121, "range_max": 300, "count": 3800, "percentage": 33.0},
                        {"range_min": 301, "range_max": None, "count": 2600, "percentage": 22.6}
                    ]
                },
                "device_breakdown": {
                    "by_category": [
                        {"device_category": 1, "segment_value": "Desktop", "visits": 6900, "percentage": 60.0, "avg_page_views": 6.3, "avg_duration_sec": 230, "single_page_visits": 900}
                    ],
                    "by_os": [
                        {"segment_value": "Windows", "visits": 4600, "percentage": 40.0, "avg_page_views": 6.1, "avg_duration_sec": 219, "single_page_visits": 600}
                    ],
                    "by_browser": [
                        {"segment_value": "Chrome", "visits": 5750, "percentage": 50.0, "avg_page_views": 5.9, "avg_duration_sec": 201, "single_page_visits": 950}
                    ],
                    "by_screen_orientation": [
                        {"segment_value": "landscape", "visits": 8050, "percentage": 70.0, "avg_page_views": 6.1, "avg_duration_sec": 213, "single_page_visits": 1200}
                    ]
                },
                "traffic_sources": {
                    "by_search_engine": [
                        {"segment_value": "google", "visits": 5750, "percentage": 50.0, "avg_page_views": 5.98, "avg_duration_sec": 207, "single_page_visits": 950}
                    ]
                },
                "geographic_distribution": {
                    "top_cities": [
                        {"segment_value": "Moscow", "visits": 3450, "percentage": 30.0, "avg_page_views": 6.3, "avg_duration_sec": 230, "single_page_visits": 450}
                    ]
                },
                "page_metrics": [
                    {"url": "/home", "title": "Home", "visits_as_entry": 5750, "visits_as_exit": 2100, "total_hits": 9200, "unique_visitors": 5175, "visits_with_single_page": 900, "subsequent_page_diversity": 17}
                ],
                "navigation_patterns": {
                    "reverse_navigation": {"visits_with_reverse_nav": 2300, "percentage": 20.0, "total_reverse_transitions": 4025},
                    "common_transitions": [
                        {"from_url": "/home", "to_url": "/products", "transition_count": 3450}
                    ],
                    "loop_patterns": [
                        {"sequence": ["/products", "/detail", "/products"], "occurrences": 575}
                    ]
                },
                "funnel_metrics": {
                    "application_funnel": [
                        {"step": 1, "url": "/home", "visits_entered": 11500, "visits_completed": 8050}
                    ]
                },
                "session_complexity_metrics": {
                    "high_interaction_sessions": {"sessions_with_10plus_pages": 1150, "percentage": 10.0, "avg_pages": 17.8, "avg_duration_sec": 518, "avg_unique_urls": 14.1},
                    "url_revisit_patterns": {"sessions_with_url_revisits": 2875, "percentage": 25.0, "avg_revisits_per_session": 3.2, "avg_unique_urls_revisited": 2.2}
                }
            }
        ],
        "metadata": {
            "project_name": "Test Project",
            "generated_at": "2024-01-31T12:00:00Z",
            "data_source": "analytics_db"
        }
    }
    
    st.session_state.analysis_result = simulated_result
    st.session_state.last_update = datetime.now()

# Display results
if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    
    # Display metadata
    st.info(f"📊 Project: {result['metadata']['project_name']}")
    st.info(f"🕒 Generated at: {result['metadata']['generated_at']}")
    st.info(f"💾 Data source: {result['metadata']['data_source']}")
    
    if len(result['releases']) >= 2:
        release1 = result['releases'][0]
        release2 = result['releases'][1]
        
        # Display comparison
        display_metrics_comparison(release1, release2)
        
        # Display improvements
        display_improvements(release1, release2)
        
        # Create tabs for different metrics
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Session Distribution", 
            "💻 Device Breakdown", 
            "🌐 Top Pages", 
            "🌍 Geographic Distribution"
        ])
        
        with tab1:
            display_session_distributions(release1, release2)
        
        with tab2:
            display_device_breakdown(release1, release2)
        
        with tab3:
            display_top_pages(release1, release2)
        
        with tab4:
            display_geographic_distribution(release1, release2)
        
        # Raw JSON output
        with st.expander("Raw JSON Response"):
            st.json(result)
    else:
        st.error("Invalid result format - expected at least 2 releases")
else:
    st.info("Waiting for analysis results...")