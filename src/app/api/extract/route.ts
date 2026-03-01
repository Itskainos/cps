import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import fs from "fs";
import path from "path";
import { promisify } from "util";
import os from "os";

const execAsync = promisify(exec);

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();
        const file = formData.get("file") as File;

        if (!file) {
            return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
        }

        // Prepare temp file path
        const tempDir = os.tmpdir();
        const tempFilePath = path.join(tempDir, `${Date.now()}-${file.name}`);

        // Save uploaded file to temp path
        const buffer = Buffer.from(await file.arrayBuffer());
        await fs.promises.writeFile(tempFilePath, buffer);

        // Call Python script
        const scriptPath = path.join(process.cwd(), "api/ocr_engine.py");

        // Try both "python" and "python3"
        let pythonCmd = "python";
        try {
            await execAsync("python --version");
        } catch {
            pythonCmd = "python3";
        }

        const { stdout, stderr } = await execAsync(`${pythonCmd} "${scriptPath}" "${tempFilePath}"`);

        // Clean up
        await fs.promises.unlink(tempFilePath);

        if (stderr) {
            console.error("Python Stderr:", stderr);
        }

        try {
            const results = JSON.parse(stdout);
            return NextResponse.json(results);
        } catch (parseError) {
            console.error("Error parsing Python output:", stdout);
            return NextResponse.json({ error: "Invalid extraction output" }, { status: 500 });
        }

    } catch (error: any) {
        console.error("Main Error:", error);
        return NextResponse.json({ error: error.message || "Extraction Failed" }, { status: 500 });
    }
}
