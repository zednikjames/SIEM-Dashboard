(async () => {
    try {
        const response = await fetch('/api/return_users')

        if (!response.ok) {
            console.error('Could not load users:', response.status);
            return;
        }

        const users = await response.json();
        const tableBody = document.getElementById('user-list-body')

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
            tableBody.appendChild(row);

        }
    } catch (error) {
        console.error('Could not load users:', error);
    }

})();