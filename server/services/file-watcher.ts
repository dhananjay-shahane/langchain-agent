import chokidar from "chokidar";
import path from "path";
import fs from "fs";
import { storage } from "../storage";

// Watch data folder for new LAS files
const dataWatcher = chokidar.watch(path.join(process.cwd(), "data"), {
  ignored: /(^|[\/\\])\../, // ignore dotfiles
  persistent: true
});

dataWatcher.on("add", async (filepath) => {
  const filename = path.basename(filepath);
  
  if (filename.endsWith(".las")) {
    try {
      const stats = fs.statSync(filepath);
      const sizeInMB = (stats.size / (1024 * 1024)).toFixed(2);
      
      const lasFile = await storage.addLasFile({
        filename,
        filepath,
        size: `${sizeInMB}MB`,
        source: "manual", // Auto-detected files from data folder
        processed: false
      });
      
      // Emit to all connected clients
      global.io?.emit("new_las_file", lasFile);
      global.io?.emit("files_updated");
      
      console.log(`New LAS file detected: ${filename}`);
    } catch (error) {
      console.error(`Error adding LAS file ${filename}:`, error);
    }
  }
});

// Watch output folder for generated files
const outputWatcher = chokidar.watch(path.join(process.cwd(), "output"), {
  ignored: /(^|[\/\\])\../, // ignore dotfiles
  persistent: true
});

outputWatcher.on("add", async (filepath) => {
  const filename = path.basename(filepath);
  
  if (filename.endsWith(".png") || filename.endsWith(".jpg") || filename.endsWith(".pdf")) {
    try {
      const outputFile = await storage.addOutputFile({
        filename,
        filepath,
        type: "plot"
      });
      
      // Emit to all connected clients
      global.io?.emit("new_output_file", outputFile);
      global.io?.emit("files_updated");
      
      console.log(`New output file generated: ${filename}`);
    } catch (error) {
      console.error(`Error adding output file ${filename}:`, error);
    }
  }
});

console.log("File watchers initialized for data/ and output/ folders");
