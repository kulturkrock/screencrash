# Inventory component
Inventory component for screencrash, with support for items and achievements. Custom made specifically for the show Apornas ö.
Run component to handle backend calls and then add a web view with the `media`-component to visualize the result, or visit webpage at http://localhost:4218.
Manual changes can be done through screencrash commands or via the update subpage (http://localhost:4218/update).

Available items and achivements can be set up with configuration files. See more in [Required resources](#required-resources)

## Requirements
NodeJS v15.0+ . Make is nice but not required.

## Required resources
To customize the inventory to your liking a number of resources (mainly images) are needed. The root folder for all of these files are `public/inventory-data`:
| File                                 | Type  | Dimensions | Description                                                                                              |
| ------------------------------------ | ----- | ---------- | -------------------------------------------------------------------------------------------------------- |
| inventory-data.json                  | JSON  | N/A        | Data file describing available items and achievements. See chapter below for format.                     |
| theme/inventory-background.png       | Image | 960x720    | Background image for inventory                                                                           |
| theme/inventory-item-border-even.png | Image | 100x100    | Item border for odd items                                                                                |
| theme/inventory-item-border-odd.png  | Image | 100x100    | Item border for even items                                                                               |
| theme/inventory-money-icon.png       | Image | 100x100    | Icon for money, will be displayed as first item                                                          |
| achievements/<achievement_name>.jpg  | Image | 192x192    | Icons for each achievement. Put in achievements folder and name according to name in inventory-data.json |
| items/<item_name>.jpg                | Image | 100x100    | Icons for each item. Put in items folder and name according to name in inventory-data.json               |
|                                      |       |            |                                                                                                          |

An example of all files required to run an inventory is located in `example_data`.

### inventory-data.json format
This JSON structure contains two main keys - "items" and "achivements". Items are a list where each item is given on the form
```
{"name": "myitemname", "description": "Something for the human eye", "cost": 100}
```

Achievements can be a bit more complex since it can be auto-evaluated based on which items the user have aqcuired. A semi-complex example of this would be:
```
{
    "items": [
        {"name":"flower", "description": "This is a normal flower", "cost":0},
        {"name":"rose", "description": "Red rose", "cost":0},
        {"name":"otheritem", "description": "Some non-relevant item", "cost": 2}
    ],
    "achievements": {
		"threeflowers": {
            "title": "Flower collector", "desc": "Collect three flowers",
            "requirements": [
                {"items": ["flower", "rose"], "amount": 3}
            ]
        }
    }
```
This example first declares that we have three items: `flower`, `rose` and `otheritem`. To get the achievement called `threeflowers` we need the user to collect at least 3 out of the items `flower` and/or `rose`. So whenever the user picks up two flowers and a rose, or one flower and two roses, or three roses, or three flowers, the achivement will trigger.

For more examples see `example_data/inventory-data/inventory-data.json`.

## Running the server

### Running with make
The following commands start the component `make dev`

### Running with npm
```
npm ci
npm run dev
```