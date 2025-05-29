import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from typing import Dict, List, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

class LIMEAnalyzer:
    """Analyzer for LIME term usage in Task 3 Group B prompts"""
    
    def __init__(self):
        """Initialize the LIME analyzer"""
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.highlights_dir = os.path.join(self.data_dir, 'highlights')
        self.reports_dir = os.path.join(self.data_dir, 'reports')
        
        # Ensure directories exist
        for directory in [self.data_dir, self.highlights_dir, self.reports_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def load_lime_usage_data(self) -> Dict:
        """Load LIME usage data from analytics files"""
        try:
            # Try to load dedicated LIME analytics
            lime_file = os.path.join(self.highlights_dir, 'lime_term_usage.json')
            if os.path.exists(lime_file):
                with open(lime_file, 'r') as f:
                    lime_data = json.load(f)
                logger.info(f"Loaded LIME usage data from {lime_file}")
                return lime_data
            
            # Fallback to general highlight analytics
            highlight_file = os.path.join(self.highlights_dir, 'highlight_analytics.json')
            if os.path.exists(highlight_file):
                with open(highlight_file, 'r') as f:
                    highlight_data = json.load(f)
                if 'statistics' in highlight_data and 'lime_term_stats' in highlight_data['statistics']:
                    logger.info(f"Loaded LIME stats from highlight analytics")
                    return highlight_data['statistics']['lime_term_stats']
            
            logger.warning("No LIME usage data found")
            return {}
        except Exception as e:
            logger.error(f"Error loading LIME usage data: {str(e)}")
            return {}
    
    def load_task3_group_b_prompts(self) -> List[Dict]:
        """Load Task 3 Group B prompts from analytics files"""
        prompts = []
        
        try:
            # Try dedicated prompt analytics file
            prompt_file = os.path.join(self.highlights_dir, 'prompt_analytics_task_3.jsonl')
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r') as f:
                    for line in f:
                        prompt_data = json.loads(line.strip())
                        if prompt_data.get('group') == 'B':
                            prompts.append(prompt_data)
                
                logger.info(f"Loaded {len(prompts)} Task 3 Group B prompts from {prompt_file}")
                return prompts
            
            # Try LIME usage file
            lime_file = os.path.join(self.highlights_dir, 'lime_term_usage.json')
            if os.path.exists(lime_file):
                with open(lime_file, 'r') as f:
                    lime_data = json.load(f)
                if 'prompts' in lime_data:
                    logger.info(f"Loaded {len(lime_data['prompts'])} prompts from LIME usage file")
                    return lime_data['prompts']
            
            logger.warning("No Task 3 Group B prompts found")
            return []
        except Exception as e:
            logger.error(f"Error loading Task 3 Group B prompts: {str(e)}")
            return []
    
    def analyze_lime_term_usage(self) -> Dict:
        """Analyze LIME term usage in Task 3 Group B prompts"""
        lime_data = self.load_lime_usage_data()
        prompts = self.load_task3_group_b_prompts()
        
        if not lime_data and not prompts:
            logger.warning("No data available for LIME term analysis")
            return {"error": "No data available"}
        
        # Get term usage from LIME data or calculate from prompts
        term_usage = {}
        if 'term_usage' in lime_data:
            term_usage = lime_data['term_usage']
        elif prompts:
            # Calculate term usage from prompts
            term_counter = Counter()
            for prompt in prompts:
                if 'lime_coverage' in prompt and 'matched_terms' in prompt['lime_coverage']:
                    term_counter.update(prompt['lime_coverage']['matched_terms'])
            term_usage = dict(term_counter)
        
        # Calculate statistics
        total_usage = sum(term_usage.values())
        term_percentages = {term: (count / total_usage * 100) if total_usage > 0 else 0 
                           for term, count in term_usage.items()}
        
        # Calculate prompt-level statistics
        prompt_stats = {}
        if prompts:
            prompt_stats = {
                'total_prompts': len(prompts),
                'avg_lime_terms_per_prompt': sum(len(p.get('lime_coverage', {}).get('matched_terms', [])) 
                                              for p in prompts) / len(prompts) if prompts else 0,
                'prompts_with_lime_terms': sum(1 for p in prompts 
                                             if p.get('lime_coverage', {}).get('matched_terms', []))
            }
        
        return {
            'term_usage': term_usage,
            'term_percentages': term_percentages,
            'total_usage': total_usage,
            'prompt_stats': prompt_stats
        }
    
    def generate_lime_usage_report(self) -> Dict:
        """Generate a report on LIME term usage in Task 3 Group B prompts"""
        analysis = self.analyze_lime_term_usage()
        
        if 'error' in analysis:
            return analysis
        
        # Create visualizations
        try:
            # Term usage bar chart
            term_usage = analysis['term_usage']
            sorted_terms = sorted(term_usage.items(), key=lambda x: x[1], reverse=True)
            
            plt.figure(figsize=(10, 6))
            plt.bar([t[0] for t in sorted_terms], [t[1] for t in sorted_terms])
            plt.title('LIME Term Usage in Task 3 Group B Prompts')
            plt.xlabel('LIME Term')
            plt.ylabel('Usage Count')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save the chart
            chart_path = os.path.join(self.reports_dir, 'lime_term_usage_chart.png')
            plt.savefig(chart_path)
            plt.close()
            
            # Create report
            report = {
                'analysis': analysis,
                'visualizations': {
                    'term_usage_chart': chart_path
                },
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            # Save report
            report_path = os.path.join(self.reports_dir, 'lime_term_usage_report.json')
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Generated LIME usage report at {report_path}")
            return report
        except Exception as e:
            logger.error(f"Error generating LIME usage report: {str(e)}")
            return {
                'error': f"Error generating report: {str(e)}",
                'partial_analysis': analysis
            }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create analyzer and generate report
    analyzer = LIMEAnalyzer()
    report = analyzer.generate_lime_usage_report()
    
    if 'error' not in report:
        print(f"LIME usage report generated successfully.")
        print(f"Total LIME term usage: {report['analysis']['total_usage']}")
        print(f"Term usage: {report['analysis']['term_usage']}")
    else:
        print(f"Error: {report['error']}")
