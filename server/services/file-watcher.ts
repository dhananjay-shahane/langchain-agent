import chokidar from "chokidar";
import path from "path";
import fs from "fs";
import { storage } from "../storage";

// Track processed files to prevent duplicates
const processedLasFiles = new Set<string>();
const processedOutputFiles = new Set<string>();

// Watch data folder for new LAS files
const dataWatcher = chokidar.watch(path.join(process.cwd(), "data"), {
  ignored: /(^|[\/\\])\../, // ignore dotfiles
  persistent: true,
  ignoreInitial: false // We'll handle initial files manually
});

let isInitialScan = true;

dataWatcher.on("ready", () => {
  isInitialScan = false;
  console.log("Data folder initial scan complete");
});

dataWatcher.on("add", async (filepath) => {
  const filename = path.basename(filepath);
  
  if (filename.endsWith(".las")) {
    // Check if we've already processed this file
    if (processedLasFiles.has(filepath)) {
      return;
    }
    
    try {
      // Check if file already exists in storage
      const existingFiles = await storage.getLasFiles();
      const alreadyExists = existingFiles.some(f => f.filename === filename && f.filepath === filepath);
      
      if (alreadyExists) {
        processedLasFiles.add(filepath);
        return;
      }
      
      const stats = fs.statSync(filepath);
      const sizeInMB = (stats.size / (1024 * 1024)).toFixed(2);
      
      const lasFile = await storage.addLasFile({
        filename,
        filepath,
        size: `${sizeInMB}MB`,
        source: "manual", // Auto-detected files from data folder
        processed: false
      });
      
      processedLasFiles.add(filepath);
      
      // Only emit events and log for truly new files (not initial scan)
      if (!isInitialScan) {
        global.io?.emit("new_las_file", lasFile);
        global.io?.emit("files_updated");
        console.log(`New LAS file detected: ${filename}`);
      }
    } catch (error) {
      console.error(`Error adding LAS file ${filename}:`, error);
    }
  }
});

// Watch output folder for generated files
const outputWatcher = chokidar.watch(path.join(process.cwd(), "output"), {
  ignored: /(^|[\/\\])\../, // ignore dotfiles
  persistent: true,
  ignoreInitial: false
});

let isOutputInitialScan = true;

outputWatcher.on("ready", () => {
  isOutputInitialScan = false;
  console.log("Output folder initial scan complete");
});

outputWatcher.on("add", async (filepath) => {
  const filename = path.basename(filepath);
  
  if (filename.endsWith(".png") || filename.endsWith(".jpg") || filename.endsWith(".pdf")) {
    // Check if we've already processed this file
    if (processedOutputFiles.has(filepath)) {
      return;
    }
    
    try {
      // Check if file already exists in storage
      const existingFiles = await storage.getOutputFiles();
      const alreadyExists = existingFiles.some(f => f.filename === filename && f.filepath === filepath);
      
      if (alreadyExists) {
        processedOutputFiles.add(filepath);
        return;
      }
      
      const outputFile = await storage.addOutputFile({
        filename,
        filepath,
        type: "plot"
      });
      
      processedOutputFiles.add(filepath);
      
      // Only emit events and log for truly new files (not initial scan)
      if (!isOutputInitialScan) {
        global.io?.emit("new_output_file", outputFile);
        global.io?.emit("files_updated");
        console.log(`New output file generated: ${filename}`);
      }
    } catch (error) {
      console.error(`Error adding output file ${filename}:`, error);
    }
  }
});

console.log("File watchers initialized for data/ and output/ folders");
