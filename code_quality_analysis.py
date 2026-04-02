#!/usr/bin/env python3
"""
Comprehensive code quality analysis to simulate CodeRabbit-style nitpicks.
"""

import ast
import os
import sys
import re
from typing import List, Dict, Any
from pathlib import Path

class CodeQualityAnalyzer:
    """Analyze code for common issues and nitpicks."""
    
    def __init__(self):
        self.issues = []
        self.stats = {
            'files_analyzed': 0,
            'lines_of_code': 0,
            'issues_found': 0,
            'categories': {}
        }
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            lines = content.split('\n')
            
            file_issues = []
            
            # Check various code quality issues
            file_issues.extend(self.check_imports(tree, lines))
            file_issues.extend(self.check_docstrings(tree, lines))
            file_issues.extend(self.check_naming(tree, lines))
            file_issues.extend(self.check_complexity(tree, lines))
            file_issues.extend(self.check_security(tree, lines))
            file_issues.extend(self.check_best_practices(tree, lines))
            file_issues.extend(self.check_type_hints(tree, lines))
            file_issues.extend(self.check_error_handling(tree, lines))
            
            self.stats['files_analyzed'] += 1
            self.stats['lines_of_code'] += len(lines)
            self.stats['issues_found'] += len(file_issues)
            
            return {
                'file': file_path,
                'issues': file_issues,
                'lines': len(lines)
            }
            
        except Exception as e:
            return {
                'file': file_path,
                'error': str(e),
                'issues': []
            }
    
    def check_imports(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check import-related issues."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Check for unused imports
                    if alias.name.startswith('.'):
                        issues.append({
                            'type': 'import_style',
                            'line': node.lineno,
                            'message': f'Relative import "{alias.name}" should be absolute',
                            'severity': 'warning'
                        })
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('.'):
                    issues.append({
                        'type': 'import_style',
                        'line': node.lineno,
                        'message': f'Relative import from "{node.module}" should be absolute',
                        'severity': 'warning'
                    })
        
        return issues
    
    def check_docstrings(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check docstring presence and quality."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                # Check if function/class has docstring
                if (node.body and 
                    not isinstance(node.body[0], ast.Expr) and
                    not (isinstance(node.body[0], ast.Expr) and 
                          isinstance(node.body[0].value, ast.Constant) and 
                          isinstance(node.body[0].value.value, str))):
                    
                    issues.append({
                        'type': 'documentation',
                        'line': node.lineno,
                        'message': f'{node.__class__.__name__} "{node.name}" missing docstring',
                        'severity': 'info'
                    })
        
        return issues
    
    def check_naming(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check naming conventions."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check function naming (snake_case)
                if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                    issues.append({
                        'type': 'naming',
                        'line': node.lineno,
                        'message': f'Function "{node.name}" should use snake_case naming',
                        'severity': 'style'
                    })
            
            elif isinstance(node, ast.ClassDef):
                # Check class naming (PascalCase)
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                    issues.append({
                        'type': 'naming',
                        'line': node.lineno,
                        'message': f'Class "{node.name}" should use PascalCase naming',
                        'severity': 'style'
                    })
        
        return issues
    
    def check_complexity(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check cyclomatic complexity."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    issues.append({
                        'type': 'complexity',
                        'line': node.lineno,
                        'message': f'Function "{node.name}" has complexity {complexity} (max 10)',
                        'severity': 'warning'
                    })
        
        return issues
    
    def check_security(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check security issues."""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Check for hardcoded passwords/secrets
            if re.search(r'(password|secret|key)\s*=\s*["\'].*["\']', line, re.IGNORECASE):
                issues.append({
                    'type': 'security',
                    'line': i,
                    'message': 'Potential hardcoded secret detected',
                    'severity': 'critical'
                })
            
            # Check for SQL injection vulnerabilities
            if re.search(r'execute\s*\(\s*["\'].*%.*["\']', line):
                issues.append({
                    'type': 'security',
                    'line': i,
                    'message': 'Potential SQL injection vulnerability - use parameterized queries',
                    'severity': 'critical'
                })
            
            # Check for eval/exec usage
            if re.search(r'\b(eval|exec)\s*\(', line):
                issues.append({
                    'type': 'security',
                    'line': i,
                    'message': 'Use of eval/exec is dangerous',
                    'severity': 'critical'
                })
        
        return issues
    
    def check_best_practices(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check Python best practices."""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Check for bare except
            if re.search(r'except\s*:', line):
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'message': 'Bare except clause - specify exception types',
                    'severity': 'warning'
                })
            
            # Check for print statements (should use logging)
            if re.search(r'\bprint\s*\(', line):
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'message': 'Use logging instead of print',
                    'severity': 'info'
                })
        
        return issues
    
    def check_type_hints(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check type hint usage."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if function has type hints
                if not node.returns:
                    issues.append({
                        'type': 'type_hints',
                        'line': node.lineno,
                        'message': f'Function "{node.name}" missing return type hint',
                        'severity': 'info'
                    })
                
                # Check arguments have type hints
                for arg in node.args.args:
                    if not arg.annotation:
                        issues.append({
                            'type': 'type_hints',
                            'line': node.lineno,
                            'message': f'Parameter "{arg.arg}" missing type hint',
                            'severity': 'info'
                        })
        
        return issues
    
    def check_error_handling(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Check error handling patterns."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                # Check if raise has proper exception
                if isinstance(node.exc, ast.Name) and node.exc.id == 'Exception':
                    issues.append({
                        'type': 'error_handling',
                        'line': node.lineno,
                        'message': 'Raise specific exceptions, not generic Exception',
                        'severity': 'warning'
                    })
        
        return issues
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                              ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler)):
                complexity += 1
        return complexity
    
    def analyze_directory(self, directory: str, pattern: str = "*.py") -> Dict[str, Any]:
        """Analyze all Python files in directory."""
        results = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    result = self.analyze_file(file_path)
                    results.append(result)
        
        return {
            'summary': self.stats,
            'results': results
        }

def main():
    """Run code quality analysis on refactored code."""
    analyzer = CodeQualityAnalyzer()
    
    print("🔍 Running Code Quality Analysis (CodeRabbit-style)")
    print("=" * 60)
    
    # Analyze payment domain
    print("\n🏦 Analyzing Payment Domain...")
    payment_results = analyzer.analyze_directory('backend/apps/payments')
    
    # Analyze music domain
    print("\n🎵 Analyzing Music Domain...")
    music_results = analyzer.analyze_directory('temp_music_domain')
    
    # Analyze shared infrastructure
    print("\n🔧 Analyzing Shared Infrastructure...")
    shared_results = analyzer.analyze_directory('backend/shared')
    
    # Generate report
    all_results = payment_results['results'] + music_results['results'] + shared_results['results']
    
    print("\n📊 ANALYSIS RESULTS")
    print("=" * 60)
    
    # Categorize issues
    categories = {}
    severity_count = {'critical': 0, 'warning': 0, 'info': 0, 'style': 0}
    
    for result in all_results:
        if 'error' in result:
            continue
            
        for issue in result['issues']:
            category = issue['type']
            severity = issue['severity']
            
            if category not in categories:
                categories[category] = []
            categories[category].append(issue)
            severity_count[severity] += 1
    
    # Print summary
    print(f"Files Analyzed: {analyzer.stats['files_analyzed']}")
    print(f"Lines of Code: {analyzer.stats['lines_of_code']}")
    print(f"Issues Found: {analyzer.stats['issues_found']}")
    print(f"\nSeverity Breakdown:")
    print(f"  Critical: {severity_count['critical']} 🔴")
    print(f"  Warning: {severity_count['warning']} 🟡")
    print(f"  Info: {severity_count['info']} 🔵")
    print(f"  Style: {severity_count['style']} 🟠")
    
    # Print detailed issues by category
    for category, issues in categories.items():
        if issues:
            print(f"\n📋 {category.upper()} ISSUES ({len(issues)}):")
            print("-" * 40)
            
            # Group by file
            by_file = {}
            for issue in issues:
                file_path = issue.get('file', 'unknown')
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(issue)
            
            for file_path, file_issues in by_file.items():
                print(f"\n📄 {file_path}")
                for issue in file_issues[:5]:  # Show first 5 issues per file
                    severity_icon = {
                        'critical': '🔴',
                        'warning': '🟡', 
                        'info': '🔵',
                        'style': '🟠'
                    }.get(issue['severity'], '⚪')
                    
                    print(f"  {severity_icon} Line {issue['line']}: {issue['message']}")
                
                if len(file_issues) > 5:
                    print(f"  ... and {len(file_issues) - 5} more issues")
    
    # Generate recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("=" * 60)
    
    if severity_count['critical'] > 0:
        print("🚨 CRITICAL: Fix security issues immediately")
    
    if severity_count['warning'] > 0:
        print("⚠️  WARNING: Address warnings to improve code quality")
    
    if categories.get('documentation', []):
        print("📚 Add missing docstrings for better documentation")
    
    if categories.get('type_hints', []):
        print("🏷️  Add type hints for better code clarity")
    
    if categories.get('naming', []):
        print("📝 Follow naming conventions (PEP 8)")
    
    if categories.get('best_practice', []):
        print("✨ Follow Python best practices")
    
    print(f"\n🎯 OVERALL QUALITY SCORE: {max(0, 100 - analyzer.stats['issues_found'])}/100")
    
    return {
        'summary': analyzer.stats,
        'categories': categories,
        'severity_count': severity_count
    }

if __name__ == "__main__":
    main()
