const fullnameValue = document.getElementById("fullname");
const roleValue = document.getElementById("role");
const profile_picture = document.getElementById("profile-pic");

(async () => {
	const response = await fetch('/api/get_user_info');

    const data = await response.json();

    if (response.ok) {
        const fullname = data.fullname
        const role = data.role
        const picture = data.profile_picture ?? "default.png";

        fullnameValue.textContent = fullname;
        roleValue.textContent = role;
        profile_picture.src = '/static/profile-pictures/' + encodeURIComponent(picture);
        
    } else {
        console.log(data.error)
    }

})();