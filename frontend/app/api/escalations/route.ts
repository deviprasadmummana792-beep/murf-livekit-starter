import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import path from "path";
import { promisify } from "util";

const execPromise = promisify(exec);

// Path to helper script
const HELPER_PATH = path.resolve(process.cwd(), "lib/db_helper.py");

export async function GET() {
  try {
    const cmd = `python "${HELPER_PATH}" list`;
    const { stdout, stderr } = await execPromise(cmd);
    if (stderr) {
      console.error("DB helper stderr:", stderr);
    }
    const data = JSON.parse(stdout.trim());
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Failed to list escalations:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const { reference_id, status } = await request.json();
    if (!reference_id || !status) {
      return NextResponse.json({ error: "Missing reference_id or status" }, { status: 400 });
    }

    const cmd = `python "${HELPER_PATH}" update "${reference_id}" "${status}"`;
    const { stdout, stderr } = await execPromise(cmd);
    if (stderr) {
      console.error("DB helper stderr:", stderr);
    }

    const res = JSON.parse(stdout.trim());
    if (res.success) {
      return NextResponse.json({ success: true });
    } else {
      return NextResponse.json({ error: "Failed to update escalation" }, { status: 500 });
    }
  } catch (error: any) {
    console.error("Failed to update escalation:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
