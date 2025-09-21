#!/usr/bin/env python3
"""
Convert .env file to TOML format for Streamlit Cloud secrets
"""

def env_to_toml(env_file='.env', output_file='secrets.toml'):
    """Convert .env file to TOML format"""
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()

        toml_lines = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Split on first = only
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                toml_lines.append(f'{key} = "{value}"')

        # Write to output file
        with open(output_file, 'w') as f:
            f.write('\n'.join(toml_lines))

        print(f"✅ Converted {env_file} to {output_file}")
        print("\nTOML content:")
        print('\n'.join(toml_lines))

    except FileNotFoundError:
        print(f"❌ File {env_file} not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    env_to_toml()