"""
Script to load dict.cc dictionary file into PostgreSQL database.
"""
import re
import os
import sys
from typing import Optional, List, Tuple
import psycopg2
from psycopg2.extras import execute_batch

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_gender(text: str) -> Tuple[str, str]:
    """Extract gender markers like {m}, {f}, {n}, {pl} from text."""
    gender_pattern = r'\{(m|f|n|pl|m\.pl|f\.pl)\}'
    match = re.search(gender_pattern, text)
    if match:
        gender = match.group(1)
        # Remove gender from text
        cleaned_text = re.sub(gender_pattern, '', text).strip()
        return gender, cleaned_text
    return None, text


def extract_brackets_info(text: str) -> Tuple[List[str], str]:
    """Extract information in square brackets [...]."""
    bracket_pattern = r'\[([^\]]+)\]'
    matches = re.findall(bracket_pattern, text)
    # Remove all brackets from text
    cleaned_text = re.sub(bracket_pattern, '', text).strip()
    return matches, cleaned_text


def parse_line(line: str) -> Optional[dict]:
    """Parse a single line from dict.cc file."""
    # Skip comments and empty lines
    if line.startswith('#') or not line.strip():
        return None
    
    # Split by tabs
    parts = line.split('\t')
    if len(parts) < 2:
        return None
    
    word_source = parts[0].strip()
    word_target = parts[1].strip()
    word_class = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    tags_field = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
    
    # Extract gender from source word
    gender_source, word_source_clean = extract_gender(word_source)
    
    # Extract gender from target word
    gender_target, word_target_clean = extract_gender(word_target)
    
    # Extract brackets info from source
    source_brackets, word_source_final = extract_brackets_info(word_source_clean)
    
    # Extract brackets info from target
    target_brackets, word_target_final = extract_brackets_info(word_target_clean)
    
    # Parse subject tags from tags field
    subject_tags = []
    if tags_field:
        tag_matches = re.findall(r'\[([^\]]+)\]', tags_field)
        subject_tags.extend(tag_matches)
    
    # Combine all brackets info for additional_info fields
    additional_info_source = ' '.join(source_brackets) if source_brackets else None
    additional_info_target = ' '.join(target_brackets) if target_brackets else None
    
    # Extract usage context (common markers like [Bras.], [col.], [ugs.], [fig.])
    usage_markers = []
    for bracket in source_brackets + target_brackets:
        if any(marker in bracket for marker in ['Bras.', 'Port.', 'col.', 'ugs.', 'fig.']):
            usage_markers.append(bracket)
    usage_context = ' '.join(usage_markers) if usage_markers else None
    
    return {
        'word_source': word_source_final.strip(),
        'word_target': word_target_final.strip(),
        'gender_source': gender_source,
        'gender_target': gender_target,
        'word_class': word_class,
        'subject_tags': subject_tags if subject_tags else None,
        'additional_info_source': additional_info_source,
        'additional_info_target': additional_info_target,
        'usage_context': usage_context,
        'raw_entry': line.strip(),
        'language_pair': 'pt-de',
        'source_language': 'pt',
        'target_language': 'de'
    }


def load_dict_cc_file(file_path: str, db_connection_string: str, batch_size: int = 1000):
    """Load dict.cc file into PostgreSQL database."""
    
    print(f"Loading file: {file_path}")
    
    # Connect to database
    conn = psycopg2.connect(db_connection_string)
    cursor = conn.cursor()
    
    # Prepare insert statement
    insert_query = """
        INSERT INTO dict_cc_translations (
            word_source, word_target, gender_source, gender_target,
            word_class, subject_tags, additional_info_source, additional_info_target,
            usage_context, raw_entry, language_pair, source_language, target_language
        ) VALUES (
            %(word_source)s, %(word_target)s, %(gender_source)s, %(gender_target)s,
            %(word_class)s, %(subject_tags)s, %(additional_info_source)s, %(additional_info_target)s,
            %(usage_context)s, %(raw_entry)s, %(language_pair)s, %(source_language)s, %(target_language)s
        )
    """
    
    batch = []
    total_inserted = 0
    skipped = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                parsed = parse_line(line)
                
                if parsed is None:
                    skipped += 1
                    continue
                
                batch.append(parsed)
                
                # Insert batch when it reaches batch_size
                if len(batch) >= batch_size:
                    execute_batch(cursor, insert_query, batch)
                    conn.commit()
                    total_inserted += len(batch)
                    print(f"Inserted {total_inserted} entries... (line {line_num})")
                    batch = []
        
        # Insert remaining entries
        if batch:
            execute_batch(cursor, insert_query, batch)
            conn.commit()
            total_inserted += len(batch)
        
        print(f"\n✓ Successfully inserted {total_inserted} entries")
        print(f"✓ Skipped {skipped} lines (comments/empty)")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Configuration
    DICT_FILE = r"c:\Users\CarstenSchweiger\Documents\Language Decoder\GitRepoLangDec\dictionaries\dict_cc\cnddngdgnn-871494015-797995.txt"
    
    # Get database connection string from environment variable
    DB_CONNECTION = os.getenv('DATABASE_URL')
    
    if not DB_CONNECTION:
        print("Error: DATABASE_URL environment variable not set")
        print("\nPlease set it like:")
        print('$env:DATABASE_URL="postgresql://user:password@host/database?sslmode=require"')
        sys.exit(1)
    
    if not os.path.exists(DICT_FILE):
        print(f"Error: File not found: {DICT_FILE}")
        sys.exit(1)
    
    # Load the dictionary
    load_dict_cc_file(DICT_FILE, DB_CONNECTION, batch_size=1000)
