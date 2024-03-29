## Meteorsys 🚀

![coverage](https://user-images.githubusercontent.com/11026970/185807569-c5ff67f9-e687-45c6-ba1d-8d02f304730e.svg)

Meteorsys is the ultimate solution for automating tasks related to Responsys emails. 

The script provides 2 functionalities:

### Parsing Content

The script helps a developer to parse the content of a Responsys email template. The script automatically parses:

 - child modules used within the email template

- Responsys template tags and queries

- Responsys tables used within the email template

### Scan For a Keyword within a Folder

The script also allows the developer to scan the contents of a Responsys folder for a keyword. 

Let’s suppose you want to fetch all the modules which uses the keyword `SOMEVARIABLE`. This option allows you to do that.


## How to Use It

1. Provide your Responsys username and password in the `.env` file provided.

    The `.env` file contains the API endpoints and the necessary credentials to access those endpoints.

2. Create a new virtualenv & activate it and install these packages like so:

    `pip install -r requirements.txt`

You are good to go now! Just run the script:

    python meteorsys.py

## Switches

The first time you run the program, it’ll ask you to input an option:

`Enter option: (parse content (p) | scan for keyword (s)`

Enter `p` to parse for queries or `s` to scan a keyword within a folder.

Then, the program asks you to input folder names where the modules to be parsed are located:

`Enter the folder name: modules`

Then, the program asks you to input the modules names to be parsed:

`Enter the input module names (,): generic`

Then, the user has to provide some configurations.
- The first configuration allows the user to find and print table schemes. Type in `y` to confirm.
- The second configuration allows the user to print the HTML content of the module. Type in `y` to confirm.
- The final configuration allows the user to find the child modules. Type in `y` to confirm.

```
Find tables? : y
Print content? : y
Find containing modules? : y
```

Finally, the program outputs something like this based on your choice:

**************************************************************************************************** 
```
Will use Module Name as input. Module Name: 'contentlibrary/modules/generic.htm'
Finding containing modules switch: ON
Will find this many modules including itself: 10
Finding tables switch: ON
Print queries switch: ON
Print content switch: ON 
```
****************************************************************************************************

This example indicates that (in the same order):

- a Module Name is given as an input and will be used to parse Responsys Queries and Template Tags

- The program will find the child modules within the input module

- The program will find up to 10 modules including itself

- The program will find supplemental tables and print their schema for each module

- The program will print queries and template tags used in the module

- The program will print the HTML content of the module

 To control these switches, you can refer to this code block, which is located in `config.html`:

```python
FIND_CONTAINING_MODULES = True
FIND_CONTAINING_MODULES_DEPTH = 10
FIND_TABLES = True
PRINT_QUERIES = True
PRINT_CONTENT = True
USE_CAMPAIGN_NAME = False
UPDATE_CONTENT = False
```
