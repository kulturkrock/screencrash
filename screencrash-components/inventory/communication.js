
import WebSocket from "ws";
import anzip from "anzip";
import crypto from "crypto";
import { writeFile, readFile, existsSync } from "fs";
import { promisify } from "util";

class CommunicationModel {

    constructor(inventory) {
        this.componentId =
          process.env.SCREENCRASH_COMPONENT_ID ||
          crypto.randomBytes(8).toString("hex");
        this.coreConnection = null;
        this.connections = [];
        this.inventory = inventory;
        this._setupInventoryEvents();
        this._setupCoreSocket();

        try {
            this.reloadInventory();
        } catch (e) {
            console.log("Failed to load static data");
        }
    }

    _setupInventoryEvents() {
        this.inventory.addEventListener("added_item", this._sendItemAddedUpdate.bind(this));
        this.inventory.addEventListener("removed_item", this._sendItemRemovedUpdate.bind(this));
        this.inventory.addEventListener("items", this._sendItemsUpdate.bind(this));
        this.inventory.addEventListener("changed_money", this._sendMoneyUpdate.bind(this));
        this.inventory.addEventListener("achievement", this._sendAchievementUpdate.bind(this));
        this.inventory.addEventListener("achievements", this._sendAchievementsUpdate.bind(this));
        this.inventory.addEventListener("achievement_reached", this._sendAchievementReachedUpdate.bind(this));
        this.inventory.addEventListener("items_visibility", this._sendItemsVisibilityUpdate.bind(this));
    }

    _setupCoreSocket() {
        const addr = `ws://${process.env.SCREENCRASH_CORE || "localhost:8001"}/`;
        this.coreConnection = new WebSocket(addr);
        this.coreConnection.onopen = () => {
            console.log("Connected to core");
            this._sendToCore({
                type: "announce",
                client: "inventory",
                channel: 1
            });
        };
        this.coreConnection.onmessage = (event) => {
            this.handleMessage(event.data);
        };
        this.coreConnection.onclose = () => {
            console.log("Lost connection to core, reconnecting in 2s...");
            setTimeout(this._setupCoreSocket.bind(this), 2000);
        };
        this.coreConnection.onerror = () => {
            console.log("Error on core socket. Closing connection...");
        };
    }

    _sendItemAddedUpdate(event) {
        const item = event.data;
        this._sendToAll({ messageType: "item_add", item: item });
        this._sendItemsUpdate();
    }

    _sendItemRemovedUpdate(event) {
        const item = event.data;
        this._sendToAll({ messageType: "item_remove", item: item });
        this._sendItemsUpdate();
    }

    _sendItemsUpdate() {
        this._sendToAll({ messageType: "items", items: this.inventory.getCurrentItems() });
    }

    _sendItemsVisibilityUpdate() {
        this._sendToAll({ messageType: "items_visibility", visible: this.inventory.getItemsSectionVisibility() });
    }

    _sendMoneyUpdate(event) {
        const { current, change } = event.data;
        this._sendToAll({
            messageType: "money",
            money: current,
            changeAmount: change,
            currency: this.inventory.getCurrency(change)
        });
    }

    _sendAchievementsUpdate() {
        this._sendToAll({ messageType: "achievements", achievements: this.inventory.getCurrentAchievements() });
    }

    _sendAchievementUpdate(event) {
        const achievement = event.data;
        this._sendToAll({ messageType: "achievement", achievement: achievement });
        this._sendAchievementsUpdate();
    }

    _sendAchievementReachedUpdate(event) {
        const achievement = event.data;
        this._sendToAll({ messageType: "achievement_reached", achievement: achievement });
    }

    _sendToCore(data) {
        if (this.coreConnection !== null) {
            this.coreConnection.send(JSON.stringify(data));
        }
    }

    _sendToAll(data) {
        this._sendToCore(data);
        for (const conn of this.connections) {
            conn.send(JSON.stringify(data));
        }
    }

    _sendInitialState(sock) {
        sock.send(JSON.stringify({
            messageType: "configuration",
            data: this.inventory.getStaticData()
        }));
        sock.send(JSON.stringify({
            messageType: "items_visibility",
            visible: this.inventory.getItemsSectionVisibility()
        }));
        sock.send(JSON.stringify({
            messageType: "items",
            items: this.inventory.getCurrentItems()
        }));
        sock.send(JSON.stringify({
            messageType: "money",
            money: this.inventory.getCurrentMoney(),
            changeAmount: 0,
            currency: this.inventory.getCurrency(0)
        }));
        sock.send(JSON.stringify({
            messageType: "achievements",
            achievements: this.inventory.getCurrentAchievements()
        }));
    }

    _handleComponentInfoRequest() {
        this._sendToCore({
            messageType: "component_info",
            componentId: this.componentId,
            componentName: "inventory",
            status: "online"
        });
        this._sendInitialState(this.coreConnection);
    }

    async _getHashFor(filePath) {
        const readFilePromise = promisify(readFile);
        const data = await readFilePromise(filePath);
        const checksum = crypto.createHash("md5").update(data).digest("hex");
        return checksum;
    }

    async _handleReportChecksumsRequest() {
        const files = {};
        if (existsSync("public/inventory-data.zip")) {
            const hash = await this._getHashFor("public/inventory-data.zip");
            files["inventory-data.zip"] = hash;
        }
        this._sendToCore({ messageType: "file_checksums", files });
    }

    async _syncFile(filepath, data) {
        const filename = filepath.split("/").reverse()[0];
        if (filename === "inventory-data.zip") {
            const writeFilePromise = promisify(writeFile);
            const buffer = Buffer.from(data, "base64");
            const zipPath = "public/inventory-data.zip";
            await writeFilePromise(zipPath, buffer);
            await anzip(zipPath, { outputPath: "public/inventory-data", outputContent: true });
            console.log("Synced resources");
        } else {
            console.log("Got resource which isn't inventory-data.zip. Skipping to sync...");
        }
    }

    addConnection(sock) {
        this.connections.push(sock);

        sock.on("message", (msg) => this.handleMessage(msg));
        sock.on("close", () => this.removeConnection(sock));
        this._sendInitialState(sock);
    }

    removeConnection(sock) {
        const index = this.connections.indexOf(sock);
        if (index >= 0) {
            this.connections.splice(index, 1);
        }
    }

    handleMessage(messageData) {
        try {
            const message = JSON.parse(messageData);
            console.log(`Handling command ${message.command}`);
            switch (message.command) {
                case "req_component_info":
                    this._handleComponentInfoRequest();
                    break;
                case "report_checksums":
                    this._handleReportChecksumsRequest();
                    break;
                case "file":
                    this._syncFile(message.path, message.data);
                    break;
                case "buy":
                    this.inventory.buy(message.item);
                    break;
                case "sell":
                    this.inventory.sell(message.item);
                    break;
                case "add":
                    if (message.item) {
                        this.inventory.add(message.item);
                    } else if (message.items) {
                        message.items.split(",").forEach((item) => {
                            this.inventory.add(item);
                        });
                    } else {
                        console.log("No input item given to add command");
                    }
                    break;
                case "remove":
                    this.inventory.remove(message.item);
                    break;
                case "change_money":
                    this.inventory.changeMoney(message.amount);
                    break;
                case "set_items_visibility":
                    // Use to hide items section and only show achievements section
                    this.inventory.setItemsSectionVisibility(message.visible);
                    break;
                case "clear_item_animations":
                    this._sendToAll({ messageType: "clear_item_animations" });
                    break;
                case "set_currency":
                    this.inventory.setCurrency(message.currency);
                    break;
                case "enable_achievement":
                    this.inventory.enableAchievement(message.achievement);
                    break;
                case "undo_achievement":
                    this.inventory.undoAchievement(message.achievement);
                    break;
                case "setup":
                case "reset":
                    this.inventory.reset();
                    this.reloadInventory();
                    break;
                case "restart":
                    this.restart();
                    break;
                default:
                    console.log(`Unhandled command ${message.command}`);
                    break;
            }
        } catch (e) {
            console.log(`Got error when handling cmd: ${e}`);
        }
    }

    reloadInventory() {
        this.inventory.loadStaticDataFrom("public/inventory-data/inventory-data.json");
        this._sendToAll({
            messageType: "configuration",
            data: this.inventory.getStaticData()
        });
    }

    async restart() {
        // Sneaky hack. This will force nodemon to reload.
        const writeFilePromise = promisify(writeFile);
        await writeFilePromise("tmp.restart.js", `Restarting app at ${new Date().toISOString()}`);
    }

}

export { CommunicationModel };
