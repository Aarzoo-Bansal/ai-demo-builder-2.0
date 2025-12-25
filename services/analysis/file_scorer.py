# file_scorer.py

import re

# Priority scores for specific files
FILE_SCORES = {
    # Manifests (highest priority) - tells us the tech stack
    'package.json': 100,
    'requirements.txt': 100,
    'pyproject.toml': 100,
    'go.mod': 100,
    'cargo.toml': 100,
    'pom.xml': 100,
    'build.gradle': 100,
    'gemfile': 95,
    'composer.json': 95,
    
    # Documentation
    'readme.md': 95,
    'readme': 95,
    'readme.txt': 95,
    'contributing.md': 60,
    'changelog.md': 50,
    
    # Entry points
    'main.py': 90,
    'app.py': 90,
    'index.py': 90,
    'index.js': 90,
    'index.ts': 90,
    'index.tsx': 90,
    'main.js': 90,
    'main.ts': 90,
    'app.js': 85,
    'app.ts': 85,
    'app.tsx': 85,
    'main.go': 90,
    'main.rs': 90,
    
    # Config files
    'dockerfile': 70,
    'docker-compose.yml': 70,
    'docker-compose.yaml': 70,
    '.env.example': 60,
    'tsconfig.json': 50,
    'webpack.config.js': 50,
    'vite.config.js': 50,
    'next.config.js': 50,
}

# Bonus scores for path patterns
PATH_PATTERNS = [
    (r'/routes/', 40),
    (r'/api/', 40),
    (r'/controllers/', 40),
    (r'/handlers/', 35),
    (r'/pages/', 35),
    (r'/views/', 35),
    (r'/components/', 30),
    (r'/services/', 30),
    (r'/models/', 25),
    (r'/src/', 10),
    (r'/lib/', 10),
    (r'/app/', 10),
]

# Patterns to skip (low value files)
SKIP_PATTERNS = [
    r'node_modules/',
    r'vendor/',
    r'\.git/',
    r'dist/',
    r'build/',
    r'\.min\.js$',
    r'\.min\.css$',
    r'\.map$',
    r'\.lock$',
    r'package-lock\.json$',
    r'yarn\.lock$',
    r'\.png$',
    r'\.jpg$',
    r'\.jpeg$',
    r'\.gif$',
    r'\.svg$',
    r'\.ico$',
    r'\.woff',
    r'\.ttf$',
    r'\.eot$',
    r'\.mp4$',
    r'\.mp3$',
    r'\.pdf$',
    r'\.zip$',
    r'\.tar$',
    r'\.gz$',
    r'__pycache__/',
    r'\.pyc$',
    r'\.test\.',
    r'\.spec\.',
    r'_test\.go$',
]


def should_skip(path: str) -> bool:
    """
    Check if file should be skipped
    
    Args:
        path: file path
    
    Returns:
        True if file should be skipped
    """
    path_lower = path.lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, path_lower):
            return True
    return False


def score_file(path: str, size: int = 0) -> int:
    """
    Score a file based on its path and size
    
    Args:
        path: file path (e.g., "src/index.js")
        size: file size in bytes
    
    Returns:
        int: score (higher = more important)
    """
    # Skip unwanted files
    if should_skip(path):
        return -1
    
    # Skip very large files (> 500KB)
    if size > 500000:
        return -1
    
    score = 0
    path_lower = path.lower()
    filename = path_lower.split('/')[-1]
    
    # Check exact filename match
    if filename in FILE_SCORES:
        score += FILE_SCORES[filename]
    
    # Check path patterns
    for pattern, bonus in PATH_PATTERNS:
        if re.search(pattern, path_lower):
            score += bonus
            break  # Only apply one path bonus
    
    # Small bonus for shorter paths (likely more important)
    depth = path.count('/')
    if depth <= 1:
        score += 5
    
    return score


def get_high_value_files(files: list, max_files: int = 10) -> list:
    """
    Score all files and return top N most important
    
    Args:
        files: list of {"path": "...", "size": ...}
        max_files: maximum number of files to return
    
    Returns:
        list of file paths (strings)
    """
    # Score each file
    scored_files = []
    for file in files:
        path = file.get("path", "")
        size = file.get("size", 0)
        score = score_file(path, size)
        
        if score >= 0:  # Skip files with -1 score
            scored_files.append({
                "path": path,
                "score": score
            })
    
    # Sort by score (highest first)
    scored_files.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top N file paths
    top_files = [f["path"] for f in scored_files[:max_files]]
    
    return top_files