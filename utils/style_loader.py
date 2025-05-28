import streamlit as st

def load_styles():
    """Load shared styles with theme detection and adaptive styling"""
    
    # Add theme detection JavaScript and CSS variables
    st.markdown("""
    <script>
        // Detect theme and set a CSS variable
        const updateTheme = () => {
            const isDark = window.parent.document.querySelector('.stApp').classList.contains('dark');
            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        }
        
        // Run immediately and set up a mutation observer to detect theme changes
        updateTheme();
        const observer = new MutationObserver(() => {
            updateTheme();
        });
        
        if (window.parent.document.querySelector('.stApp')) {
            observer.observe(window.parent.document.querySelector('.stApp'), {
                attributes: true,
                attributeFilter: ['class']
            });
        }
    </script>
    
    <style>
        /* Define theme variables */
        :root[data-theme="light"] {
            --bg-color: #f0f2f6;
            --text-color: #31333F;
            --accent-color: #f63366;
            --border-color: #e0e0e0;
            --highlight-bg: #e6f3ff;
            --highlight-text: #0068c9;
            --task-bg: #e7f5ff;
            --task-border: #0068c9;
            --task-text: #31333F;
            --note-bg: #f0f0f0;
            --note-border: #d0d0d0;
        }
        
        :root[data-theme="dark"] {
            --bg-color: #0e1117;
            --text-color: #fafafa;
            --accent-color: #f63366;
            --border-color: #303030;
            --highlight-bg: #1e2a3a;
            --highlight-text: #6c8ec9;
            --task-bg: #162536;
            --task-border: #4d8bc9;
            --task-text: #f0f2f6;
            --note-bg: #1e1e1e;
            --note-border: #444444;
        }
        
        /* Task container styling */
        .task-container {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: var(--task-bg) !important;
            border: 1px solid var(--task-border) !important;
            margin-bottom: 1rem;
            color: var(--task-text) !important;
        }
        
        .task-container h3, 
        .task-container h4, 
        .task-container p, 
        .task-container strong,
        .task-container div {
            color: var(--task-text) !important;
        }
        
        /* Clinical note styling */
        .clinical-note {
            line-height: 1.8;
            font-size: 18px !important;
            margin: 15px 0;
            padding: 15px;
            background-color: var(--note-bg) !important;
            border: 1px solid var(--note-border) !important;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            color: var(--text-color) !important;
        }
        
        .clinical-note p, 
        .clinical-note div, 
        .clinical-note span, 
        .clinical-note strong {
            font-size: 18px !important;
            color: var(--text-color) !important;
        }
        
        /* Highlight styles */
        .highlight-red {
            display: inline-block;
            padding: 2px 4px;
            margin: 0 2px;
            border-radius: 3px;
            background-color: rgba(220, 53, 69, 0.37);
            color: var(--text-color) !important;
            font-weight: 500;
            font-size: 18px !important;
        }
        
        .highlight-blue {
            display: inline-block;
            padding: 2px 4px;
            margin: 0 2px;
            border-radius: 3px;
            background-color: rgba(0, 123, 255, 0.23);
            color: var(--text-color) !important;
            font-weight: 500;
            font-size: 18px !important;
        }
        
        /* Make highlight legends visible in both themes */
        .highlight-legend-red {
            color: rgb(220, 53, 69) !important;
            font-weight: 600;
            font-size: 18px !important;
        }
        
        .highlight-legend-blue {
            color: rgb(0, 123, 255) !important;
            font-weight: 600;
            font-size: 18px !important;
        }
        
        /* Survey styling */
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stRadio"] label,
        div[data-testid="stTextArea"] label {
            font-size: 18px !important;
        }
    </style>
    """, unsafe_allow_html=True)
