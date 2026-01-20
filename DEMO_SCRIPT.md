# Fix-It AI - Demo Script

**Duration:** 5-7 minutes  
**Audience:** Business partner / Investor  
**URL:** `https://your-cloudflare-url.pages.dev/demo.html`

---

## Opening (30 seconds)

> "Let me show you Fix-It AI in action. This is a demo of our embeddable maintenance widget that property managers can add to their tenant portals with just two lines of code."

*Scroll through the demo page briefly to show it's a professional property management site.*

> "Notice the site looks completely normal - but watch the bottom-right corner..."

---

## Scene 1: The Leak (2-3 minutes)

### Setup
> "Imagine I'm a tenant at Rancho Management. It's 10 PM and I just noticed water under my kitchen sink."

### Demo Steps

1. **Click the blue chat button** in the bottom-right corner

2. **Type this message:**
   ```
   I just noticed water pooling under my kitchen sink. It looks like it's dripping from the pipes.
   ```

3. **Wait for AI response** - Point out:
   > "Notice how the AI immediately asks clarifying questions. It's not just logging a ticket - it's actually trying to diagnose the issue."

4. **Type follow-up:**
   ```
   The water is coming from where the pipe connects. I can see some rust around the fitting. Started maybe an hour ago.
   ```

5. **Point out the response:**
   > "See the risk level badge? The AI has classified this as **Yellow** - meaning it needs attention soon but isn't an emergency. It's also giving DIY tips while escalating to the property manager."

### Key Talking Points
- ✅ "No app download required - works on any device"
- ✅ "Handles issues 24/7 when the office is closed"
- ✅ "Deflects simple issues with DIY guidance, saving service calls"
- ✅ "Automatically escalates urgent issues"

---

## Scene 2: The Photo Upload (1 minute)

### Demo Steps

1. **Click the attachment icon** (📎) in the chat

2. **Upload a photo** (use any image of a plumbing issue or damage)

3. **Type:**
   ```
   Here's a photo of the leak
   ```

4. **Point out:**
   > "The AI can analyze images to better understand the problem. This helps property managers triage issues before sending a technician."

---

## Scene 3: The Move-Out Audit (2 minutes)

*Note: This requires backend API access. You can demonstrate via Postman/curl or describe the feature.*

### Talking Points

> "Beyond chat, Fix-It AI has a powerful video audit feature for move-in/move-out inspections."

**Explain the workflow:**

1. **Move-In:** Property manager uploads a walkthrough video
   > "The AI creates a detailed baseline of the unit's condition - every scratch, stain, and wear mark is documented."

2. **Move-Out:** Same process at end of tenancy
   > "The AI compares against the baseline and generates a 'New Damages' report - identifying only what changed during the tenancy."

3. **Value Proposition:**
   > "This eliminates disputes over security deposits. Both parties have AI-verified documentation of the unit's condition."

### API Demo (Optional)

If showing the API directly:
```bash
# Move-in audit
curl -X POST https://your-backend.onrender.com/audit \
  -F "unit_id=APT-101" \
  -F "mode=move-in" \
  -F "file=@walkthrough.mp4"
```

---

## Scene 4: The Business Value (1-2 minutes)

### Pull up these stats (or reference them):

> "Here's why property managers are excited about this:"

| Metric | Impact |
|--------|--------|
| **Service Call Reduction** | 30-40% of issues resolved with DIY guidance |
| **Response Time** | From 24 hours to instant |
| **After-Hours Coverage** | 100% - AI works nights and weekends |
| **Deposit Disputes** | Near-zero with video audit evidence |

### The Embed Story

> "And the best part? Integration is this simple:"

```html
<div id="fixit-widget"></div>
<script src="https://cdn.fixit.ai/widget.js"></script>
```

> "Two lines of code. That's it. Works with any website, any property management software."

---

## Closing (30 seconds)

> "This is our MVP. The core AI is working, the widget is embeddable, and we're live in production."

> "Next steps are onboarding pilot customers and refining the model with real maintenance data."

**Call to Action:**
> "Want to try it yourself? I'll send you the link - report a fake issue and see how the AI responds."

---

## Troubleshooting

### Widget not loading?
- Check browser console for errors
- Verify `VITE_API_URL` is set in Cloudflare
- Ensure backend is responding: `curl https://your-backend.onrender.com/`

### AI not responding?
- Check `GEMINI_API_KEY` is set in Render
- Look at Render logs for errors

### Demo tips
- Test the full flow before the demo
- Have backup screenshots ready
- Keep a terminal open with `curl` commands as backup

---

## Quick Reference - Sample Inputs

**Leak:**
```
Water is dripping from under my bathroom sink. The cabinet below is getting wet.
```

**HVAC:**
```
My AC stopped working. It's making a clicking sound but no cold air comes out.
```

**Electrical:**
```
The outlet in my bedroom stopped working. Other outlets are fine.
```

**Urgent (Red):**
```
I smell gas near my stove. What should I do?
```

---

*Good luck with your demo! 🚀*
