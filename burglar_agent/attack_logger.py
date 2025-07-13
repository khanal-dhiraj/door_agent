"""
Advanced logging and analysis system for burglar agent attacks
Tracks attack patterns, success rates, and provides insights
"""

import json
import logging
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import matplotlib.pyplot as plt


@dataclass
class AttackLog:
    """Structured attack log entry"""
    timestamp: str
    strategy: str
    success: bool
    duration: float
    door_variation: str
    transcripts: List[str]
    password_attempt: Optional[str] = None
    error_message: Optional[str] = None
    audio_file: Optional[str] = None
    target_analysis: Optional[Dict] = None


class AttackAnalyzer:
    """Analyzes attack patterns and success rates"""
    
    def __init__(self, db_path: str = "attack_analytics.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for attack logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                strategy TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                duration REAL NOT NULL,
                door_variation TEXT,
                password_attempt TEXT,
                error_message TEXT,
                audio_file TEXT,
                transcripts TEXT,
                target_analysis TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                strategy TEXT PRIMARY KEY,
                total_attempts INTEGER DEFAULT 0,
                successful_attempts INTEGER DEFAULT 0,
                avg_duration REAL DEFAULT 0,
                last_success TEXT,
                success_rate REAL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_attack(self, attack_log: AttackLog):
        """Log an attack attempt to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO attacks (
                timestamp, strategy, success, duration, door_variation,
                password_attempt, error_message, audio_file, transcripts, target_analysis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            attack_log.timestamp,
            attack_log.strategy,
            attack_log.success,
            attack_log.duration,
            attack_log.door_variation,
            attack_log.password_attempt,
            attack_log.error_message,
            attack_log.audio_file,
            json.dumps(attack_log.transcripts),
            json.dumps(attack_log.target_analysis) if attack_log.target_analysis else None
        ))
        
        # Update strategy performance
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_performance (
                strategy, total_attempts, successful_attempts, avg_duration, last_success, success_rate
            ) VALUES (
                ?,
                COALESCE((SELECT total_attempts FROM strategy_performance WHERE strategy = ?), 0) + 1,
                COALESCE((SELECT successful_attempts FROM strategy_performance WHERE strategy = ?), 0) + ?,
                (
                    SELECT AVG(duration) FROM attacks WHERE strategy = ?
                ),
                CASE WHEN ? THEN ? ELSE (SELECT last_success FROM strategy_performance WHERE strategy = ?) END,
                (
                    SELECT CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100
                    FROM attacks WHERE strategy = ?
                )
            )
        ''', (
            attack_log.strategy,
            attack_log.strategy,
            attack_log.strategy,
            1 if attack_log.success else 0,
            attack_log.strategy,
            attack_log.success,
            attack_log.timestamp,
            attack_log.strategy,
            attack_log.strategy
        ))
        
        conn.commit()
        conn.close()
    
    def get_strategy_performance(self) -> List[Dict]:
        """Get performance metrics for all strategies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT strategy, total_attempts, successful_attempts, 
                   avg_duration, last_success, success_rate
            FROM strategy_performance
            ORDER BY success_rate DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'strategy': row[0],
                'total_attempts': row[1],
                'successful_attempts': row[2],
                'avg_duration': row[3],
                'last_success': row[4],
                'success_rate': row[5]
            })
        
        conn.close()
        return results
    
    def get_attacks_by_timeframe(self, hours: int = 24) -> List[Dict]:
        """Get attacks within specified timeframe"""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM attacks 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', (since,))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            attack_dict = dict(zip(columns, row))
            if attack_dict['transcripts']:
                attack_dict['transcripts'] = json.loads(attack_dict['transcripts'])
            if attack_dict['target_analysis']:
                attack_dict['target_analysis'] = json.loads(attack_dict['target_analysis'])
            results.append(attack_dict)
        
        conn.close()
        return results
    
    def get_door_variation_analysis(self) -> Dict:
        """Analyze success rates by door variation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT door_variation,
                   COUNT(*) as total_attempts,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_attempts,
                   AVG(duration) as avg_duration,
                   CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100 as success_rate
            FROM attacks
            WHERE door_variation IS NOT NULL
            GROUP BY door_variation
            ORDER BY success_rate DESC
        ''')
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                'total_attempts': row[1],
                'successful_attempts': row[2],
                'avg_duration': row[3],
                'success_rate': row[4]
            }
        
        conn.close()
        return results
    
    def generate_attack_report(self, output_file: str = None) -> str:
        """Generate comprehensive attack analysis report"""
        report_lines = []
        
        # Header
        report_lines.append("=" * 60)
        report_lines.append("BURGLAR AGENT - ATTACK ANALYSIS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 60)
        
        # Overall statistics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), SUM(CASE WHEN success THEN 1 ELSE 0 END) FROM attacks')
        total_attacks, successful_attacks = cursor.fetchone()
        
        if total_attacks > 0:
            overall_success_rate = (successful_attacks / total_attacks) * 100
            report_lines.append(f"\nOVERALL STATISTICS:")
            report_lines.append(f"Total Attacks: {total_attacks}")
            report_lines.append(f"Successful Attacks: {successful_attacks}")
            report_lines.append(f"Overall Success Rate: {overall_success_rate:.1f}%")
        
        # Strategy performance
        strategy_perf = self.get_strategy_performance()
        if strategy_perf:
            report_lines.append(f"\nSTRATEGY PERFORMANCE:")
            report_lines.append("-" * 40)
            for strategy in strategy_perf:
                report_lines.append(f"{strategy['strategy']:<25} | "
                                  f"Success: {strategy['successful_attempts']}/{strategy['total_attempts']} "
                                  f"({strategy['success_rate']:.1f}%) | "
                                  f"Avg Duration: {strategy['avg_duration']:.1f}s")
        
        # Door variation analysis
        door_analysis = self.get_door_variation_analysis()
        if door_analysis:
            report_lines.append(f"\nDOOR VARIATION ANALYSIS:")
            report_lines.append("-" * 40)
            for variation, stats in door_analysis.items():
                report_lines.append(f"{variation:<30} | "
                                  f"Success: {stats['successful_attempts']}/{stats['total_attempts']} "
                                  f"({stats['success_rate']:.1f}%) | "
                                  f"Avg Duration: {stats['avg_duration']:.1f}s")
        
        # Recent attacks
        recent_attacks = self.get_attacks_by_timeframe(24)
        if recent_attacks:
            report_lines.append(f"\nRECENT ATTACKS (Last 24 hours):")
            report_lines.append("-" * 40)
            for attack in recent_attacks[:10]:  # Show last 10
                status = "SUCCESS" if attack['success'] else "FAILED"
                report_lines.append(f"{attack['timestamp'][:19]} | "
                                  f"{attack['strategy']:<20} | "
                                  f"{status:<7} | "
                                  f"{attack['duration']:.1f}s")
        
        # Password discoveries
        cursor.execute('SELECT password_attempt, COUNT(*) FROM attacks WHERE password_attempt IS NOT NULL GROUP BY password_attempt')
        passwords = cursor.fetchall()
        if passwords:
            report_lines.append(f"\nDISCOVERED PASSWORDS:")
            report_lines.append("-" * 40)
            for password, count in passwords:
                report_lines.append(f"{password}: {count} times")
        
        conn.close()
        
        report = "\n".join(report_lines)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
        
        return report
    
    def plot_success_rates(self, output_file: str = "success_rates.png"):
        """Generate visualization of success rates by strategy"""
        strategy_perf = self.get_strategy_performance()
        
        if not strategy_perf:
            return
        
        strategies = [s['strategy'] for s in strategy_perf]
        success_rates = [s['success_rate'] for s in strategy_perf]
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(strategies, success_rates, color='skyblue', edgecolor='navy')
        
        # Add value labels on bars
        for bar, rate in zip(bars, success_rates):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{rate:.1f}%', ha='center', va='bottom')
        
        plt.title('Attack Success Rates by Strategy')
        plt.xlabel('Strategy')
        plt.ylabel('Success Rate (%)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    def export_data(self, output_file: str = "attack_data.csv"):
        """Export attack data to CSV for further analysis"""
        conn = sqlite3.connect(self.db_path)
        
        # Read attacks table into pandas DataFrame
        df = pd.read_sql_query('SELECT * FROM attacks', conn)
        
        # Clean up JSON fields for CSV export
        df['transcripts'] = df['transcripts'].apply(
            lambda x: str(x) if x else ''
        )
        df['target_analysis'] = df['target_analysis'].apply(
            lambda x: str(x) if x else ''
        )
        
        df.to_csv(output_file, index=False)
        conn.close()


class RealTimeLogger:
    """Real-time logging for active attacks"""
    
    def __init__(self, log_file: str = "realtime_attack.log"):
        self.log_file = log_file
        self.logger = logging.getLogger('realtime_attack')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def log_conversation_turn(self, speaker: str, message: str, strategy: str = None):
        """Log individual conversation turns"""
        extra_info = f" [{strategy}]" if strategy else ""
        self.logger.info(f"{speaker.upper()}{extra_info}: {message}")
    
    def log_strategy_change(self, old_strategy: str, new_strategy: str, reason: str = ""):
        """Log strategy adaptation"""
        self.logger.info(f"STRATEGY CHANGE: {old_strategy} → {new_strategy} ({reason})")
    
    def log_target_analysis_update(self, analysis: Dict):
        """Log target analysis updates"""
        self.logger.info(f"TARGET ANALYSIS: {json.dumps(analysis, indent=None)}")
    
    def log_attack_start(self, strategy: str, target: str = "door_agent"):
        """Log attack initiation"""
        self.logger.info(f"ATTACK START: Strategy={strategy}, Target={target}")
    
    def log_attack_end(self, success: bool, duration: float, password: str = None):
        """Log attack completion"""
        status = "SUCCESS" if success else "FAILED"
        password_info = f", Password={password}" if password else ""
        self.logger.info(f"ATTACK END: {status}, Duration={duration:.1f}s{password_info}")
    
    def log_audio_event(self, event_type: str, details: str = ""):
        """Log audio-related events"""
        self.logger.info(f"AUDIO {event_type.upper()}: {details}")


# Global instances for easy access
attack_analyzer = AttackAnalyzer()
realtime_logger = RealTimeLogger()


def log_attack_attempt(strategy: str, success: bool, duration: float, 
                      transcripts: List[str], door_variation: str = None,
                      password_attempt: str = None, error_message: str = None,
                      audio_file: str = None, target_analysis: Dict = None):
    """Convenience function to log an attack attempt"""
    
    attack_log = AttackLog(
        timestamp=datetime.now().isoformat(),
        strategy=strategy,
        success=success,
        duration=duration,
        door_variation=door_variation,
        transcripts=transcripts,
        password_attempt=password_attempt,
        error_message=error_message,
        audio_file=audio_file,
        target_analysis=target_analysis
    )
    
    attack_analyzer.log_attack(attack_log)
    
    # Also log to realtime logger
    status = "SUCCESS" if success else "FAILED"
    realtime_logger.logger.info(
        f"LOGGED ATTACK: {strategy} | {status} | {duration:.1f}s | "
        f"Password: {password_attempt or 'None'}"
    )


if __name__ == "__main__":
    # Demo/test the logging system
    analyzer = AttackAnalyzer()
    
    # Generate a sample report
    report = analyzer.generate_attack_report("sample_report.txt")
    print(report)
    
    # Plot success rates if there's data
    try:
        analyzer.plot_success_rates()
        print("Success rate chart saved to success_rates.png")
    except Exception as e:
        print(f"Could not generate chart: {e}")
    
    # Export data
    try:
        analyzer.export_data()
        print("Data exported to attack_data.csv")
    except Exception as e:
        print(f"Could not export data: {e}")