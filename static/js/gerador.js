document.getElementById('save').addEventListener('click', function (event) {
    const buttonText = document.getElementById('button-text');
    const spinner = document.getElementById('spinner');

    // Substitui o texto pelo spinner
    buttonText.classList.add('d-none'); // Oculta o texto
    spinner.classList.remove('d-none'); // Mostra o spinner

    // Opcional: Impedir múltiplos cliques no botão
    this.setAttribute('disabled', 'true');
});
