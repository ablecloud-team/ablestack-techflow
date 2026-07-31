import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const [source, output] = process.argv.slice(2);
if (!source || !output) {
  throw new Error("usage: node build_template_inspect.mjs <source.pptx> <output.ndjson>");
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,image,table,chart",
  maxChars: 200000,
});
await fs.writeFile(output, `${snapshot.ndjson}\n`, "utf8");
console.log(output);
