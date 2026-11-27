let userListRequest = 0;

async function loadUsers() {
    const requestId = ++userListRequest;
    try {
        const response = await fetch('/api/return_users', { cache: 'no-store' });

        if (!response.ok) {
            console.error('Could not load users:', response.status);
            return;
        }

        const users = await response.json();
        if (requestId !== userListRequest) {
            return;
        }

        const tableBody = document.getElementById('user-list-body');
        const rows = document.createDocumentFragment();

        for (const user of users) {
            const row = document.createElement('tr');

            for (const value of [
                user.full_name,
                user.email,
                user.role,
                user.active ? 'Active' : 'Inactive',
            ]) {
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            }
            rows.appendChild(row);

        }
        tableBody.replaceChildren(rows);
    } catch (error) {
        console.error('Could not load users:', error);
    }

}

loadUsers();