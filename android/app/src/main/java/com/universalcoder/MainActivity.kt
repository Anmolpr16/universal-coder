package com.universalcoder

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class MainActivity : Activity() {
    private val client = OkHttpClient()
    private val handler = Handler(Looper.getMainLooper())
    private var pollCount = 0
    private val maxPolls = 600

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }
        val endpoint = EditText(this).apply {
            hint = "Coder API (HTTPS recommended)"
            setText("https://127.0.0.1:8765")
            singleLine = true
        }
        val token = EditText(this).apply {
            hint = "API token (optional on trusted local servers)"
            inputType = 0x81 // textPassword
            singleLine = true
        }
        val task = EditText(this).apply {
            hint = "What should I build/fix?"
            minLines = 5
            gravity = 48
        }
        val run = Button(this).apply { text = "RUN CODER" }
        val output = TextView(this).apply { textSize = 14f }
        root.addView(endpoint)
        root.addView(token)
        root.addView(task)
        root.addView(run)
        root.addView(output, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)

        run.setOnClickListener {
            val base = endpoint.text.toString().trim().trimEnd('/')
            val objective = task.text.toString().trim()
            if (objective.isEmpty()) { output.text = "Enter a task."; return@setOnClickListener }
            output.text = "Submitting..."
            val json = JSONObject().put("objective", objective).toString()
            val request = Request.Builder().url("$base/run")
                .header("Authorization", authHeader(token.text.toString()))
                .post(json.toRequestBody("application/json".toMediaType()))
                .build()
            client.newCall(request).enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) = runOnUiThread { output.text = e.message ?: e.toString() }
                override fun onResponse(call: Call, response: Response) {
                    response.use {
                        val body = it.body?.string().orEmpty()
                        if (!it.isSuccessful) {
                            runOnUiThread { output.text = "HTTP ${it.code}: $body" }
                            return
                        }
                        val result = JSONObject(body)
                        val runId = result.optString("run_id")
                        if (runId.isEmpty()) {
                            runOnUiThread { output.text = body }
                            return
                        }
                        pollCount = 0
                        runOnUiThread { output.text = "Run $runId\nStarting..." }
                        pollStatus(base, runId, token.text.toString(), output)
                    }
                }
            })
        }
    }

    private fun pollStatus(base: String, runId: String, token: String, output: TextView) {
        if (++pollCount > maxPolls) { output.text = "Timed out waiting for server status."; return }
        val request = Request.Builder().url("$base/runs/$runId")
            .header("Authorization", authHeader(token)).get().build()
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                handler.postDelayed({ pollStatus(base, runId, token, output) }, 1000)
            }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val body = it.body?.string().orEmpty()
                    if (!it.isSuccessful) { runOnUiThread { output.text = "HTTP ${it.code}: $body" }; return }
                    val json = JSONObject(body)
                    val status = json.optString("status", "unknown")
                    runOnUiThread { output.text = "Run $runId\nStatus: $status\n\n${json.optString("record", body)}" }
                    if (status == "completed" || status == "failed" || status == "not_found") return
                    handler.postDelayed({ pollStatus(base, runId, token, output) }, 1000)
                }
            }
        })
    }

    private fun authHeader(token: String): String = if (token.isBlank()) "" else "Bearer $token"
}
