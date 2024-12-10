
    // TRATAMENTO DE ERRO COM O CAMPO INPUT NUMBER - GABARITO
   
function validateNumberInput(input) {
    const errorMessage = document.getElementById('error-message');
    
    // Verifica se o valor está dentro do intervalo
    if (input.value < 1 || input.value > 4) {
        input.classList.add('is-invalid'); // Aplica estilo de erro
        errorMessage.classList.remove('d-none'); // Mostra a mensagem de erro
    } else {
        input.classList.remove('is-invalid'); // Remove estilo de erro
        errorMessage.classList.add('d-none'); // Esconde a mensagem de erro
    }
}


function adjustHeight(textarea) {
    // Reseta a altura para calcular novamente
    textarea.style.height = "auto";
    // Ajusta a altura de acordo com o scroll interno
    textarea.style.height = textarea.scrollHeight + "px";
}
