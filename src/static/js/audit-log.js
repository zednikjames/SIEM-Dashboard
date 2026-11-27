let auditLogRequest = 0;

async function loadAuditLogs() {
    const requestId = ++auditLogRequest;
    try {
        const response = await fetch('/api/return_logs', { cache: 'no-store' });

        if (!response.ok) {
            console.error('Could not load logs:', response.status);
            return;
        }

        const logs = await response.json();
        if (requestId !== auditLogRequest) {
            return;
        }
        logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        const audit_log_body = document.getElementById("audit-log-content");
        const events = document.createDocumentFragment();

        for (const log of logs) {
            const detail = document.createElement('details');
            const summary = document.createElement('summary');

            detail.classList.add('audit-event');
            summary.textContent = `${log.action} - ${log.event_id}`;
            detail.appendChild(summary);

            const fields = [
                ['ID', log.event_id],
                ['Action', log.action],
                ['Timestamp', new Date(log.timestamp).toLocaleString('en-US', {
                    dateStyle: 'medium',
                    timeStyle: 'medium',
                    hour12: true,
                })],
                ['Actor', log.actor],
                ['Target', log.target],
                ['Result', log.result ? 'Success' : 'Failure'],
                ['Details', log.details],
            ];

            for (const [label, value] of fields) {
                const paragraph = document.createElement('p');
                paragraph.textContent = `${label}: ${value ?? 'None'}`;
                detail.appendChild(paragraph);
            }

            events.appendChild(detail);
        }
        audit_log_body.replaceChildren(events);
        
    } catch (error) {
        console.error('Could not load logs:', error);
    }

}

loadAuditLogs();