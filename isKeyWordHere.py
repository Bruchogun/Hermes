from difflib import SequenceMatcher
import re

def check_containment_probability(container_str, search_str, case_sensitive=False):
    print(container_str, search_str, 'check_containment_probability')
    """
    Check how probable it is that container_str contains search_str.
    
    Args:
        container_str: The larger string to search within
        search_str: The string to search for
        case_sensitive: If False, comparison ignores case (default: False)
    
    Returns:
        Float: Probability percentage (0.0 to 100.0)
    """
    # Normalize strings if case-insensitive
    if not case_sensitive:
        container = container_str.lower()
        search = search_str.lower()
    else:
        container = container_str
        search = search_str
    
    # Handle edge cases
    if not search:
        return 100.0
    
    if not container:
        return 0.0
    
    # Method 1: Exact substring match
    if search in container:
        return 100.0
    
    # Method 1.5: Check with common separators removed (hyphens, underscores, etc.)
    container_normalized = re.sub(r'[-_.]', ' ', container)
    search_normalized = re.sub(r'[-_.]', ' ', search)
    
    if search_normalized in container_normalized or search in container_normalized:
        return 95.0
    
    # Method 2: Fuzzy matching - calculate partial matches
    
    # 2a: Check for word-level matches (considering normalized versions)
    search_words = search_normalized.split()
    container_words = container_normalized.split()
    matching_words = sum(1 for word in search_words if word in container_words)
    word_match_percent = (matching_words / len(search_words)) * 100 if search_words else 0
    
    # 2b: Check for character sequence matches
    matcher = SequenceMatcher(None, container, search)
    sequence_ratio = matcher.ratio() * 100
    
    # 2c: Check longest common substring
    match = matcher.find_longest_match(0, len(container), 0, len(search))
    longest_match_length = match.size
    longest_match_percent = (longest_match_length / len(search)) * 100
    
    # 2d: Check for all characters present (order doesn't matter)
    search_chars = set(search.replace(' ', ''))
    container_chars = set(container.replace(' ', ''))
    matching_chars = search_chars.intersection(container_chars)
    char_coverage = (len(matching_chars) / len(search_chars)) * 100 if search_chars else 0
    
    # 2e: Check for substring fragments
    fragment_matches = 0
    total_fragments = 0
    fragment_size = max(3, len(search) // 4)  # Use fragments of at least 3 chars
    
    for i in range(len(search) - fragment_size + 1):
        fragment = search[i:i+fragment_size]
        total_fragments += 1
        if fragment in container:
            fragment_matches += 1
    
    fragment_match_percent = (fragment_matches / total_fragments) * 100 if total_fragments > 0 else 0
    
    # Calculate weighted probability
    # Prioritize: word matches > fragments > longest match > character coverage
    probability = (
        word_match_percent * 0.40 +
        fragment_match_percent * 0.30 +
        longest_match_percent * 0.20 +
        char_coverage * 0.10
    )
    
    return round(probability, 2)


# Example usage
if __name__ == "__main__":
    # Interactive mode
    print("String Containment Probability Checker")
    print("="*70)
    
    container_input = input("Enter the container string (where to search): ")
    search_input = input("Enter the search string (what to find): ")
    
    probability = check_containment_probability(container_input, search_input)
    
    print(f"\nContainment Probability: {probability}%")