# PromptDoctor Data Storage and Analysis Guide

This document explains how data is collected, stored, and analyzed in the PromptDoctor system.

## Data Files and Their Purposes

### Core Data Files

- **users.csv**: User demographic and background information
- **tasks.csv**: Task completion and survey responses
- **interactions.csv**: All user interactions, including chat history, feedback, etc.
- **unified_prompts.csv**: Comprehensive prompt tracking with validation actions
- **surveys.csv**: Final survey responses

### Optional/Redundant Files
- **validation.csv**: Redundant with unified_prompts.csv (can be safely removed)
- **feedback.csv**: Redundant with interactions.csv (can be safely removed)

### Generated Analysis Files

- **complete_study_data.csv**: A merged file containing user, task, and interaction data
- **chat_history.csv/json**: Complete chat history for all users
- **analysis_dataset.csv**: Focused dataset for statistical analysis

## Where Data is Collected

### Chat History
Complete chat history is logged in `interactions.csv` with action_type "CHAT" or "MODEL_OUTPUT".
You can extract the full chat history using the `collect_chat_history()` function in `utils/data_merger.py`.

### User Feedback
Feedback on model responses is collected directly in `interactions.csv` with action_type "FEEDBACK".
No separate feedback.csv file is needed.

### Prompt Edits and Validation
Prompt validation and editing is tracked in:
1. `unified_prompts.csv` - Primary source for all prompt-related actions
2. `interactions.csv` - Backup location for all actions

Note: The `validation.csv` file is redundant and can be safely removed.

## Recommendations for Data Analysis

### For Chat Analysis
- Use `interactions.csv` with action_type "CHAT" or "MODEL_OUTPUT"
- Or use the generated `chat_history.csv` file which organizes all messages chronologically

### For Prompt Analysis
- Use `unified_prompts.csv` for all prompt-related metrics
- This includes original prompts, edited prompts, and highlighting information

### For Overall Performance
- Use `complete_study_data.csv` for comprehensive analysis
- Or use `analysis_dataset.csv` for focused statistical analysis

## Data Cleanup Utilities

For data management, use the `utils/cleanup_data.py` script to:
- Fix delimiter issues in surveys.csv
- Remove redundant files (validation.csv, feedback.csv)
- Clean up redundant timestamped merged files

Example:
```
python utils/cleanup_data.py --all
```

Or to specifically check for redundant files:
```
python utils/cleanup_data.py --redundant
```

## Data Export and Merging

To create analysis-ready datasets, use the `utils/data_merger.py` module:

```python
from utils.data_merger import DataMerger

merger = DataMerger()
# Collect complete chat history
merger.collect_chat_history()
# Merge all data into one file
merger.merge_all_data()
# Create focused analysis dataset
merger.export_analysis_dataset()
```

## Common Issues and Solutions

### surveys.csv has comma delimiter
Fix with:
```
python utils/cleanup_data.py --surveys
```

### Multiple timestamped merged files
Clean up with:
```
python utils/cleanup_data.py --merged
```

### Missing chat history
Extract with:
```python
from utils.data_merger import DataMerger
DataMerger().collect_chat_history()
```
