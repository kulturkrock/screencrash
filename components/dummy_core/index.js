const WebSocket = require('ws');
const fs = require('fs');

const wss = new WebSocket.Server({ port: 3456 });

wss.on('connection', function connection(ws) {

    console.log("Got connection!");

    ws.on('message', async function incoming(data) {
        try {
            const obj = JSON.parse(data);
            // Uncomment to test messages FROM client (may do it hard to enter commands)
            // console.log(JSON.stringify(obj));
        } catch(e){
            console.log(`Received invalid data: ${data}`);
        }
    });
});

const stdin = process.openStdin();

stdin.addListener("data", async function(d) {
    try{
        // Get input
        const input = d.toString().trim();

        // Check if we want to run sequence file
        if (input.startsWith("file ")) {
            const filePath = input.split(" ")[1]
            await runSequenceFile(filePath);
            return;
        }

        // Validate that it is JSON
        const cmd = JSON.parse(input);
        const output = JSON.stringify(cmd);

        await sendMessageToComponent(output);
    } catch(e) {
        console.log("Could not send to clients: " + e.message);
    }
});

async function runSequenceFile(filePath) {
    const content = fs.readFileSync(filePath, "utf-8");
    let prom = new Promise(resolve => resolve());
    content.split("\n").forEach(line => {
        line = line.trim();
        if (line.length == 0) {
            return; // ignore empty lines
        }

        if (line.startsWith("sleep ")) {
            // Sleep x ms
            prom = prom.then(() => sleep(parseInt(1000*parseFloat(line.split(" ")[1]))));
        }
        else {
            // Run command
            prom = prom.then(() => sendMessageToComponent(JSON.stringify(JSON.parse(line)), true));
        }
    });
    return prom;
}

function sleep(ms) {
    return new Promise(resolve => {
        console.log(`Sleeping ${ms}`);
        setTimeout(resolve, ms);
    });
}

function sendMessageToComponent(data, print_sending = false) {
    return new Promise(resolve => {
        if (print_sending) {
            console.log(`Sending ${JSON.stringify(data)}`);
        }

        // Send to all
        let count = 0;
        wss.clients.forEach(function each(client) {
            if (client.readyState === WebSocket.OPEN) {
                client.send(data);
                count++;
            }
        });
        
        // Acknowledge send status
        console.log("Message sent to %d/%d clients", count, wss.clients.size);
        resolve();
    });
}

console.log("Running WS server on port 3456, enter valid JSON to send to all clients");