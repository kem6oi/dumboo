// app/static/js/script.js

console.log("Global script.js loaded.");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded.");

    // --- Admin View Challenge: Toggle Solution Details ---
    // Moved from admin/view_challenge.html
    const showSolutionBtn = document.getElementById('show-solution-btn');
    const solutionDetailsDiv = document.getElementById('solution-details');

    if (showSolutionBtn && solutionDetailsDiv) {
        // Initially hide the details if they are not already hidden by CSS
        solutionDetailsDiv.style.display = 'none';

        showSolutionBtn.addEventListener('click', function() {
            if (solutionDetailsDiv.style.display === 'none') {
                solutionDetailsDiv.style.display = 'block';
                this.textContent = 'Hide Solution Details';
            } else {
                solutionDetailsDiv.style.display = 'none';
                this.textContent = 'Show Solution Details';
            }
        });
    }
    // Note: The script in admin/create_challenge.html for toggling crypto fields
    // should remain in that template as it's specific to that form structure.
    // Only move truly global or widely used JS here.

    // --- Add any other global JS functionality here ---
    // Example: smooth scrolling, handling modals, etc.

});

// Function to update cart item quantity via AJAX (Optional, for better UX)
// This is more advanced and requires corresponding backend route and handling
// function updateCartItem(itemId, newQuantity) {
//     fetch('/marketplace/cart/update/' + itemId, {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             // Include CSRF token if using them for AJAX requests
//             // 'X-CSRFToken': getCsrfToken() // Requires JS to get token from cookie/meta tag
//         },
//         body: JSON.stringify({ quantity: newQuantity })
//     })
//     .then(response => response.json())
//     .then(data => {
//         if (data.success) {
//             console.log('Cart updated:', data);
//             // Update UI based on response (e.g., item total, cart total)
//             window.location.reload(); // Simple reload for now
//         } else {
//             console.error('Error updating cart:', data.message);
//             alert('Error updating cart: ' + data.message);
//         }
//     })
//     .catch(error => {
//         console.error('Fetch error:', error);
//         alert('An error occurred.');
//     });
// }
