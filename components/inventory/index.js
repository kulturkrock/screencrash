import express from "express";
import expressWs from "express-ws";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { engine } from "express-handlebars";
import { hbsHelpers } from "./hbs-helpers.js";

import { CommunicationModel } from "./communication.js";
import { Inventory } from "./inventory.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

const { app } = expressWs(express());
app.engine("hbs", engine({
    extname: "hbs",
    defaultLayout: "default",
    layoutsDir: join(__dirname, "views"),
    helpers: hbsHelpers
}));
app.set("views", join(__dirname, "views"));
app.set("view engine", "hbs");
app.use(express.static("public"));

const inventory = new Inventory();
const communication = new CommunicationModel(inventory);
app.get("/", (req, res) => {
    res.render("main", {});
});
app.get("/update", (req, res) => {
    res.render("update", { availableItems: inventory.getAvailableItems(), achievementsLeft: inventory.getAvailableAchievements() });
});
app.ws("/", (sock, req) => {
    communication.addConnection(sock);
});

const port = (process.argv.length > 2 ? parseInt(process.argv[2]) : 4218);
app.listen(port, function() {
    console.log("Server running at port %s", port);
});
