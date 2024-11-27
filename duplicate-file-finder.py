import os
import hashlib
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of file content."""
    hash_sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def find_identical_files(root_dir: str) -> Dict[str, List[Tuple[str, Set[str]]]]:
    """
    Find files with identical names and content across subdirectories.
    
    Args:
        root_dir: Root directory to start the search from
    
    Returns:
        Dictionary with filename as key and list of tuples containing
        file hash and set of full paths as value
    """
    # Dictionary to store findings: filename -> [(hash1, {path1, path2}), (hash2, {path3, path4})]
    file_map = defaultdict(lambda: defaultdict(set))
    
    # Walk through all subdirectories
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            try:
                file_hash = calculate_file_hash(full_path)
                file_map[filename][file_hash].add(full_path)
            except (IOError, OSError) as e:
                print(f"Error processing {full_path}: {e}")
    
    # Convert to regular dict and filter out unique files
    result = {}
    for filename, hash_paths in file_map.items():
        # Convert to list of tuples (hash, paths) where there are multiple paths
        hash_path_list = [
            (file_hash, paths) 
            for file_hash, paths in hash_paths.items()
            if len(paths) > 1
        ]
        if hash_path_list:
            result[filename] = hash_path_list
            
    return result

def display_results(results: Dict[str, List[Tuple[str, Set[str]]]]) -> None:
    """Display the results in a readable format."""
    if not results:
        print("No identical files found.")
        return
    
    print("\nFindings:")
    print("-" * 80)
    
    for filename, hash_paths_list in results.items():
        print(f"\nFilename: {filename}")
        print("=" * 40)
        
        for file_hash, paths in hash_paths_list:
            print(f"\nHash: {file_hash}")
            print("Locations:")
            for path in sorted(paths):
                print(f"  - {path}")
        
        print("-" * 80)

def main():
   
    root_dir = os.getcwd();

    
    print(f"Scanning directory: {root_dir}")
    results = find_identical_files(root_dir)
    display_results(results)

if __name__ == "__main__":
    main()
