// Lets node:test import the web sources, which use the Next "@/" alias and
// extensionless TypeScript paths. Only project files are rewritten.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function withExtension(file) {
  if (fs.existsSync(file) && fs.statSync(file).isFile()) return file;
  for (const ext of [".ts", ".tsx", ".js", ".mjs"]) {
    if (fs.existsSync(file + ext)) return file + ext;
  }
  return file;
}

function inProject(parentURL) {
  if (!parentURL?.startsWith("file:")) return false;
  const file = fileURLToPath(parentURL);
  return file === webRoot || file.startsWith(webRoot + path.sep);
}

export function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith("@/")) {
    return nextResolve(pathToFileURL(withExtension(path.join(webRoot, specifier.slice(2)))).href, context);
  }
  if (specifier.startsWith(".") && inProject(context.parentURL)) {
    const parent = fileURLToPath(context.parentURL);
    return nextResolve(pathToFileURL(withExtension(path.resolve(path.dirname(parent), specifier))).href, context);
  }
  return nextResolve(specifier, context);
}
