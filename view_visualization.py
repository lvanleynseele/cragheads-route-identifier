import base64
import json

def save_visualization(base64_string, output_file='visualization.png'):
    """
    Save a base64-encoded image string to a PNG file.
    
    Args:
        base64_string: The base64-encoded image string
        output_file: The name of the output file (default: visualization.png)
    """
    try:
        # Decode the base64 string and save it as a PNG file
        with open(output_file, 'wb') as f:
            f.write(base64.b64decode(base64_string))
        print(f"Visualization saved as '{output_file}'")
    except Exception as e:
        print(f"Error saving visualization: {str(e)}")

def main():
    # Get the base64 string from the user
    print("Please paste the base64 string from the API response (press Ctrl+D or Ctrl+Z when done):")
    try:
        # Read multiple lines until EOF
        base64_string = ""
        while True:
            try:
                line = input()
                base64_string += line
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return

    # Remove any whitespace
    base64_string = base64_string.strip()
    
    # Save the visualization
    save_visualization(base64_string)

if __name__ == "__main__":
    main() 