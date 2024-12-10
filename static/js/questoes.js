document.getElementById('toggleGabarito').addEventListener('click', function() {
    const gabaritoSection = document.getElementById('gabaritoSection');
    const button = this;

    // Alterna a classe "d-none" para mostrar/ocultar o gabarito
    gabaritoSection.classList.toggle('d-none');

    // Altera o texto do botão
    if (gabaritoSection.classList.contains('d-none')) {
        button.textContent = 'Ver Gabarito';
    } else {
        button.textContent = 'Esconder Gabarito';
    }
});