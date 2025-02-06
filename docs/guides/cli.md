# CLI Usage

Run your snippet on the command line. This is useful so you do not have to deploy or update the snippet on each
system you want to run it on. I find this most useful when I have a commly used command to run on a remote server.

For security reasons, you can only run snippets that you have created.
This is to prevent someone editing a snippet to run malicious code as only you can edit your own snippets.

Here are some examples of how to run a snippet directly from the command line:

```bash
# Bash script example
bash <(curl -s curl -H "X-API-Key: your_api_key_here" \
http://localhost:8000/api/snippets/command/testA)

# Python script example
wget -qO- --header "X-API-Key: your_api_key_here" \
http://localhost:8000/api/snippets/command/py-a  | python -
```

If you find yourself running snippets often, you can create a bash function to make it easier to run snippets.

Update the `LANG_COMMANDS` to include the command you want to run for each language.
The file gets saved into a local file then called with the listed command.
This works better then always trying to run the script inline in the terminal as it causes less issues with escaping characters.

```bash
function dsc() {
    ###
    # devscript command
    ###

    # Configuration
    local DSC_API_KEY="${DSC_API_KEY:-YOUR_API_KEY_HERE}"
    local DSC_API_URL="${DSC_API_URL:-http://localhost:8000}"

    # Validate input
    if [ -z "$1" ]; then
        echo "Error: Snippet ID required"
        echo "Usage: dsc <snippet-id> [args...]"
        return 1
    fi

    # Language-specific command map
    declare -A LANG_COMMANDS=(
        ["bash"]="bash"
        ["python"]="python3"
        ["javascript"]="node"
        # Add more languages as needed
    )

    # Make API request with proper error handling
    local response headers
    response=$(curl -s -D - \
        -H "X-API-Key: ${DSC_API_KEY}" \
        -H "Accept: text/plain" \
        "${DSC_API_URL}/api/snippets/command/${1}")

    # Split response into headers and content
    headers=$(echo "$response" | sed '/^\r$/q')
    content=$(echo "$response" | sed '1,/^\r$/d')

    # Get HTTP status code from headers
    local http_code
    http_code=$(echo "$headers" | head -n1 | cut -d' ' -f2)

    # Check HTTP status
    if [ "$http_code" != "200" ]; then
        echo "Error: Failed to fetch snippet (HTTP ${http_code})"
        echo "$content"
        return 1
    fi

    # Get language from response headers
    local lang
    lang=$(echo "$headers" | grep -i "X-Snippet-Lang" | cut -d: -f2 | tr -d '[:space:]')

    # Create temporary file for script execution
    local tmp_file
    tmp_file=$(mktemp)
    echo "$content" > "$tmp_file"

    # Execute based on language
    local exit_code=1
    if [ -n "${LANG_COMMANDS[$lang]}" ]; then
        ${LANG_COMMANDS[$lang]} "$tmp_file" "${@:2}"
        exit_code=$?
    else
        echo "Error: Unsupported language '${lang}'"
    fi

    # Clean up temp file
    rm "$tmp_file"
    return $exit_code
}
```

Now you can run a snippet with the following command:

```bash
dsc testA arg1 arg2
```
