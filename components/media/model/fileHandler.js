const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const util = require('util');

const readFile = util.promisify(fs.readFile);
const writeFile = util.promisify(fs.writeFile);
const mkdir = util.promisify(fs.mkdir);
const readdir = util.promisify(fs.readdir);
const stat = util.promisify(fs.stat);

module.exports = class FileHandler {

    constructor(resourcesPath) {
        this.resourcesPath = resourcesPath;
    }

    getResourcesPath() {
        return this.resourcesPath;
    }

    async writeFile(message) {
        const { path: filePath, data } = message;
        // Core will send POSIX paths, but we may be on Windows
        const platformCorrectPath = filePath.split(path.posix.sep).join(path.sep);
        const fullPath = path.join(this.resourcesPath, platformCorrectPath);
        const dir = path.dirname(fullPath);
        await mkdir(dir, { recursive: true });
        const buffer = Buffer.from(data, 'base64');
        await writeFile(fullPath, buffer);
        console.log(`Wrote file ${filePath}`);
    }

    async getHashes(filePath) {
        if (filePath === undefined) {
            filePath = this.resourcesPath;
        }
        const stats = await stat(filePath);
        if (stats.isDirectory()) {
            const subPaths = (await readdir(filePath)).map((subPath) => path.join(filePath, subPath));
            const subPathHashes = await Promise.all(subPaths.map((subPath) => this.getHashes(subPath)));
            return subPathHashes.reduce((acc, curr) => ({ ...acc, ...curr }), {});
        } else {
            if (filePath.endsWith('.gitignore')) {
                return {};
            }
            const data = await readFile(filePath);
            const checksum = crypto.createHash('md5').update(data).digest('hex');
            const relativePath = path.relative(this.resourcesPath, filePath);
            // Represent as a POSIX path (forward slashes) on Windows too, since
            // Core and the component need to agree
            const posixPath = relativePath.split(path.sep).join(path.posix.sep);
            return { [posixPath]: checksum };
        }
    }

};
