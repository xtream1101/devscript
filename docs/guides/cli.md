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

Update the `command_map` to include the command to run the snippet for each language you want to support.
The script will be "piped" into that command. So for most commands, you just need to add a `-` to the end of the
command like in the examples below.

```bash
function smc(){
    declare -A command_map
    # bash is supported by default
    # Update to use the expected command for each language on your system
    command_map["python"]="python -"
    command_map["javascript"]="node -"

    # This can be declared anywhere you normally handle your env vars. But its fine to keep here too.
    SM_API_KEY="YOUR_API_KEY_HERE"

    # Get the language of the snippet
    snippetLang=$(curl -I -s -o /dev/null -w '%header{X-Snippet-Lang}' -H "X-API-Key: ${SM_API_KEY}" http://localhost:8000/api/snippets/command/${1})
    # Check if snippetLang was found in command_map, or its "bash"
    if [ -z ${command_map["$snippetLang"]} ] && [ "$snippetLang" != "bash" ]; then
        echo "Error: Unsupported language '$snippetLang'"
        return 1
    fi

    # Fetch the plain text content of the snippet
    script=$(curl -s curl -H "X-API-Key: ${SM_API_KEY}" http://localhost:8000/api/snippets/command/${1})

    if [[ "$snippetLang" == "bash" ]]; then
        bash -c "$script" ${@}
    else
        echo "$script" | eval ${command_map["$snippetLang"]} ${@:2}
    fi
    }
```

Now you can run a snippet with the following command:

```bash
smc testA arg1 arg2
```
