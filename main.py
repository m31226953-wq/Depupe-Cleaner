import os
import hashlib
import argparse
import json
from pathlib import Path
from datetime import datetime

def get_file_hash(filepath, chunk_size=8192):
    """Calculate MD5 hash of a file"""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None

def find_duplicates(directory, extensions=None, min_size=1, verbose=True):
    """Find duplicate files in directory"""
    duplicates = {}
    total_scanned = 0
    
    if verbose:
        print(f"[*] Scanning: {directory}")
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            
            try:
                size = filepath.stat().st_size
                if size < min_size:
                    continue
            except:
                continue
            
            if extensions:
                if filepath.suffix.lower() not in extensions:
                    continue
            
            file_hash = get_file_hash(filepath)
            if not file_hash:
                continue
            
            if file_hash not in duplicates:
                duplicates[file_hash] = []
            duplicates[file_hash].append(str(filepath))
            
            total_scanned += 1
            if verbose and total_scanned % 500 == 0:
                print(f"[*] Scanned: {total_scanned} files")
    
    return {k: v for k, v in duplicates.items() if len(v) > 1}

def delete_duplicates_auto(duplicates, keep_newest=True):
    """Auto delete duplicates - keeps the newest or oldest file"""
    deleted_count = 0
    freed_space = 0
    
    for hash_val, files in duplicates.items():
        # Get file info
        file_info = []
        for f in files:
            try:
                mtime = os.path.getmtime(f)
                size = os.path.getsize(f)
                file_info.append((f, mtime, size))
            except:
                continue
        
        if not file_info:
            continue
        
        # Sort by modification time (newest first or oldest first)
        if keep_newest:
            file_info.sort(key=lambda x: x[1], reverse=True)  # Keep newest
        else:
            file_info.sort(key=lambda x: x[1])  # Keep oldest
        
        # Keep first file, delete rest
        keep_file = file_info[0][0]
        duplicates_to_delete = file_info[1:]
        
        for dup_path, dup_mtime, dup_size in duplicates_to_delete:
            try:
                os.remove(dup_path)
                deleted_count += 1
                freed_space += dup_size
                print(f"[🗑️] Deleted: {dup_path}")
            except Exception as e:
                print(f"[❌] Error deleting {dup_path}: {e}")
    
    return deleted_count, freed_space

def scan_multiple_dirs(directories, extensions=None, min_size=1):
    """Scan multiple directories"""
    all_duplicates = {}
    total_dirs = len(directories)
    
    for i, directory in enumerate(directories, 1):
        print(f"\n[{i}/{total_dirs}] Processing {directory}")
        if not os.path.exists(directory):
            print(f"[⚠️] Warning: Directory not found: {directory}")
            continue
        
        dupes = find_duplicates(directory, extensions, min_size, verbose=True)
        
        # Merge duplicates
        for hash_val, files in dupes.items():
            if hash_val not in all_duplicates:
                all_duplicates[hash_val] = []
            all_duplicates[hash_val].extend(files)
    
    # Filter out unique files
    return {k: v for k, v in all_duplicates.items() if len(v) > 1}

def save_report(duplicates, deleted_count, freed_space, output_file):
    """Save report to JSON file"""
    report = {
        "date": datetime.now().isoformat(),
        "duplicate_groups": len(duplicates),
        "total_duplicates": sum(len(files) - 1 for files in duplicates.values()),
        "deleted_count": deleted_count,
        "freed_space_mb": freed_space / (1024 * 1024),
        "files": duplicates
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n[📄] Report saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Auto dedupe cleaner - finds and deletes duplicates automatically')
    parser.add_argument('directories', nargs='+', help='Directories to scan (can specify multiple)')
    parser.add_argument('-e', '--extensions', nargs='+', help='Filter by extensions (e.g., .jpg .mp4)')
    parser.add_argument('-m', '--min-size', type=int, default=1, help='Minimum file size in KB (default: 1KB)')
    parser.add_argument('-k', '--keep', choices=['newest', 'oldest'], default='newest', 
                       help='Which file to keep: newest or oldest (default: newest)')
    parser.add_argument('-r', '--report', help='Save report to JSON file')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode (less output)')
    
    args = parser.parse_args()
    
    # Prepare extensions
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                  for ext in args.extensions] if args.extensions else None
    
    print("=" * 60)
    print("🔍 DEDUPE-CLEANER - AUTO MODE 🔍")
    print("=" * 60)
    print(f"Directories: {', '.join(args.directories)}")
    print(f"Keep: {args.keep}")
    print(f"Min size: {args.min_size} KB")
    if extensions:
        print(f"Extensions: {', '.join(extensions)}")
    print("=" * 60)
    
    # Scan all directories
    duplicates = scan_multiple_dirs(args.directories, extensions, args.min_size * 1024)
    
    if not duplicates:
        print("\n[✅] No duplicates found! Your system is clean!")
        return
    
    # Show summary
    total_dupes = sum(len(files) - 1 for files in duplicates.values())
    total_size = sum(os.path.getsize(files[0]) * (len(files) - 1) 
                     for files in duplicates.values() 
                     if os.path.exists(files[0]))
    
    print("\n" + "=" * 60)
    print(f"[📊] Found: {len(duplicates)} duplicate groups")
    print(f"[📊] Total duplicate files: {total_dupes}")
    print(f"[💾] Potential space to free: {total_size / (1024*1024):.2f} MB")
    print("=" * 60)
    
    # Auto delete
    print("\n[🚀] Starting automatic deletion...")
    keep_newest = (args.keep == 'newest')
    deleted_count, freed_space = delete_duplicates_auto(duplicates, keep_newest)
    
    # Final summary
    print("\n" + "=" * 60)
    print("[✅] CLEANUP COMPLETE!")
    print(f"[🗑️] Deleted files: {deleted_count}")
    print(f"[💾] Space freed: {freed_space / (1024*1024):.2f} MB")
    print("=" * 60)
    
    # Save report if requested
    if args.report:
        save_report(duplicates, deleted_count, freed_space, args.report)

if __name__ == "__main__":
    main()