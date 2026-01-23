def parse_world(content):
    """
    Parse a YAML subset format into a Python dictionary.
    
    Supports:
    - key: value pairs
    - Nested structures with indentation (2 spaces per level)
    - Lists with dash prefix: "- item"
    - Inline lists: [1, 2, 3] or just: 1, 2, 3
    - Mixed structures (lists of dicts, nested dicts, etc.)
    """
    lines = content.strip().split('\n')
    root = {}
    stack = [(root, -1, 'dict')]  # (current_container, indent_level, container_type)
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines
        if not line.strip():
            i += 1
            continue
        
        # Calculate indentation
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        
        # Pop stack to find correct parent
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()
        
        parent, parent_indent, parent_type = stack[-1]
        
        # Check if this is a list item (starts with -)
        if stripped.startswith('- '):
            # This is a list item
            content_after_dash = stripped[2:].strip()
            
            # Ensure parent is a list
            if parent_type != 'list':
                raise ValueError(f"Line {i+1}: List item found but parent is not a list")
            
            # Check if it's a dict item (has a key: value)
            if ':' in content_after_dash:
                # This is the start of a dict within the list
                key, _, value = content_after_dash.partition(':')
                key = key.strip()
                value = value.strip()
                
                new_dict = {}
                parent.append(new_dict)
                
                if value:
                    new_dict[key] = parse_value(value)
                else:
                    # This dict has nested content
                    pass
                
                # Push this dict onto the stack for potential nested items
                stack.append((new_dict, indent, 'dict'))
            else:
                # Simple list item (just a value)
                parent.append(parse_value(content_after_dash))
            
            i += 1
            continue
        
        # Regular key: value line (check AFTER we've handled list items)
        if ':' not in stripped:
            raise ValueError(f"Line {i+1}: Expected 'key: value' or list item format in '{line}'")
        
        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip()
        
        if parent_type != 'dict':
            raise ValueError(f"Line {i+1}: Key-value pair found but parent is not a dict")
        
        # Look ahead to see if next line is a list item or nested content
        next_indent = None
        is_list = False
        is_dict = False
        
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip():
                next_stripped = next_line.lstrip()
                next_indent = len(next_line) - len(next_stripped)
                
                if next_indent > indent:
                    if next_stripped.startswith('- '):
                        is_list = True
                    else:
                        is_dict = True
        
        # Parse based on what we found
        if value:
            # Has inline value
            parent[key] = parse_value(value)
        elif is_list:
            # Next lines are list items
            new_list = []
            parent[key] = new_list
            stack.append((new_list, indent, 'list'))
        elif is_dict:
            # Next lines are nested dict items
            new_dict = {}
            parent[key] = new_dict
            stack.append((new_dict, indent, 'dict'))
        else:
            # Empty value, no nested content
            parent[key] = None
        
        i += 1
    
    return root


def parse_value(value_str):
    """
    Parse a value string into appropriate Python type.
    Supports:
    - Inline lists: [1, 2, 3]
    - Flow lists: 1, 2, 3
    - Single integers
    - Strings
    """
    value_str = value_str.strip()
    
    if not value_str:
        return None
    
    # Handle inline list syntax [...]
    if value_str.startswith('[') and value_str.endswith(']'):
        inner = value_str[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(',')]
        try:
            return [int(p) for p in parts]
        except ValueError:
            return parts
    
    # Handle comma-separated values (flow style)
    if ',' in value_str:
        parts = [p.strip() for p in value_str.split(',')]
        try:
            return [int(p) for p in parts]
        except ValueError:
            return parts
    
    # Try single integer
    try:
        return int(value_str)
    except ValueError:
        # Return as string
        return value_str

