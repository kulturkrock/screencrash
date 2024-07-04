
import { readFileSync } from "fs";

class InventoryEvent extends Event {

    constructor(type, data) {
        super(type);
        this.data = data;
    }

}

class Inventory extends EventTarget {

    constructor() {
        super();
        this.staticData = { items: [], achievements: {} };
        this.money = 0;
        this.currency = "money";
        this.currencySingular = null;
        this.itemsSectionVisibility = true;
        this.items = [];
        this.achievements = [];
        this.getAchievement = this.getAchievement.bind(this);
    }

    _add(item) {
        if (item) {
            this.items.push(item.name);
            this.dispatchEvent(new InventoryEvent("added_item", item));
        } else {
            console.log("Tried to add non-existing item");
        }
    }

    _remove(item) {
        const index = this.items.indexOf(item.name);
        if (index >= 0) {
            this.items.splice(index, 1);
            this.dispatchEvent(new InventoryEvent("removed_item", item));
            return true;
        }
        return false;
    }

    _findItem(itemName) {
        const matchingItems = this.staticData.items.filter(item => item.name === itemName);
        return matchingItems.length > 0 ? matchingItems[0] : undefined;
    }

    _countItem(itemName) {
        return this.items.filter(item => item === itemName).length;
    }

    loadStaticDataFrom(resourceFile) {
        this.staticData = JSON.parse(readFileSync(resourceFile));
        this.setCurrency(this.staticData.currency, this.staticData.currency_singular);
    }

    getStaticData() {
        return {
            items: this.staticData.items || [],
            achievements: Object.keys(this.staticData.achievements || {}).map(this.getAchievement)
        };
    }

    reset() {
        this.staticData = { items: [], achievements: {} };
        this.items = [];
        this.dispatchEvent(new InventoryEvent("items"));
        this.achievements = [];
        this.dispatchEvent(new InventoryEvent("achievements"));
        this.money = 0;
        this.dispatchEvent(new InventoryEvent("changed_money", { current: this.money, change: 0 }));
    }

    getCurrentMoney() {
        return this.money;
    }

    getCurrency(amount) {
        if ((amount === 1 || amount === -1) && this.currencySingular !== null) {
            return this.currencySingular;
        } else {
            return this.currency;
        }
    }

    getItemsSectionVisibility() {
        return this.itemsSectionVisibility;
    }

    getAvailableItems() {
        return this.staticData.items;
    }

    getCurrentItems() {
        return this.items;
    }

    getAchievement(name) {
        return {
            ...this.staticData.achievements[name],
            name: name,
            reuse: this.staticData.achievements[name].reuse === true
        };
    }

    getAvailableAchievements() {
        return Object.keys(this.staticData.achievements).map(this.getAchievement);
    }

    getCurrentAchievements() {
        return this.achievements.map(this.getAchievement);
    }

    changeMoney(amount) {
        this.money += amount;
        this.dispatchEvent(new InventoryEvent("changed_money", { current: this.money, change: amount }));
    }

    buy(itemName) {
        const item = this._findItem(itemName);
        if (item.cost > this.money) {
            return false;
        }
        this._add(item);
        this.changeMoney(-item.cost);
        this.checkAchievements();
    }

    sell(itemName) {
        const item = this._findItem(itemName);
        if (this._remove(item)) {
            this.changeMoney(item.cost);
            this.checkAchievements();
        }
    }

    add(itemName) {
        const item = this._findItem(itemName);
        this._add(item);
        this.checkAchievements();
    }

    remove(itemName) {
        const item = this._findItem(itemName);
        if (this._remove(item)) {
            this.checkAchievements();
        }
    }

    setCurrency(currency, currencySingular) {
        if (currency !== undefined && currency !== null) {
            this.currency = currency;
        }
        if (currencySingular !== undefined && currencySingular !== null) {
            this.currencySingular = currencySingular;
        }
    }

    setItemsSectionVisibility(visible) {
        if (visible !== undefined && visible !== null && this.itemsSectionVisibility !== visible) {
            this.itemsSectionVisibility = visible;
            this.dispatchEvent(new InventoryEvent("items_visibility", visible));
        }
    }

    enableAchievement(name) {
        const achievement = this.getAchievement(name);
        const hasBeenActivated = this.achievements.includes(name);
        if (achievement && (!hasBeenActivated || achievement.reuse)) {
            if (!hasBeenActivated) {
                this.achievements.push(name);
            }
            this.dispatchEvent(new InventoryEvent("achievement", achievement));
        }
    };

    undoAchievement(name) {
        const achievementIndex = this.achievements.indexOf(name);
        if (achievementIndex >= 0) {
            this.achievements.splice(achievementIndex, 1);
            this.dispatchEvent(new InventoryEvent("achievements"));
        }
    }

    checkAchievements() {
        for (const achievementName in this.staticData.achievements) {
            const achievement = this.getAchievement(achievementName);
            if ((!this.achievements.includes(achievementName) || achievement.reuse) && this.checkAchievement(achievement)) {
                this.dispatchEvent(new InventoryEvent("achievement_reached", achievement));
            }
        }
    }

    checkAchievement(achievement) {
        if (!achievement.requirements) {
            // Some achievements can only be manually triggered
            return false;
        }

        for (const req of achievement.requirements) {
            if (req.items && req.amount) {
                if (req.items.reduce((sum, x) => sum + this._countItem(x), 0) >= req.amount) {
                    return true;
                }
            } else if (req.item && req.amount) {
                if (this._countItem(req.item) >= req.amount) {
                    return true;
                }
            }
        }

        return false;
    };

}

export { Inventory };
