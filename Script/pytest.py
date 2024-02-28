my_dict = {'1': 'apple', '10': 'banana', '3': 'cherry', '22': 'date', '23': 'elderberry', '4': 'fig', '2': 'grape', '200': 'honeydew'}

# Initialize an empty list
sorted_list = []

# Iterate over the dictionary and append key-value pairs
for key, value in my_dict.items():
    try:
        key_as_int = int(key)  # Convert key to an integer
        sorted_list.append({'key': key_as_int, 'value': value})
    except ValueError:
        # Handle non-numeric keys (e.g., 'apple')
        pass

# Sort the list based on numerical keys
sorted_list.sort(key=lambda x: x['key'])

# Print the sorted list
for item in sorted_list:
    print(f"Key: {item['key']}, Value: {item['value']}")