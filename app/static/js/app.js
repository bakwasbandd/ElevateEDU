// strategy card click handler
document.querySelectorAll('.strategy-card').forEach(card => {
    card.addEventListener('click', () => {
        document.querySelectorAll('.strategy-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        const radio = card.querySelector('input[type="radio"]');
        if (radio) radio.checked = true;
    });
});
