(function () {
    const hiddenInput = document.getElementById('id_perguntas_json');
    const container = document.getElementById('perguntas-container');
    const addButton = document.getElementById('btn-add-pergunta');
    const form = document.getElementById('checklist-builder-form');

    if (!hiddenInput || !container || !addButton || !form) {
        return;
    }

    const baseQuestion = {
        enunciado: '',
        tipo: 'texto',
        obrigatoria: true,
        opcoes: []
    };

    function parseInitialQuestions() {
        if (!hiddenInput.value) {
            return [];
        }

        try {
            const parsed = JSON.parse(hiddenInput.value);
            if (!Array.isArray(parsed)) {
                return [];
            }
            return parsed;
        } catch (error) {
            return [];
        }
    }

    function renderQuestionCard(question = baseQuestion) {
        const index = container.children.length;
        const card = document.createElement('div');
        card.className = 'card checklist-question-item';

        card.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">Pergunta <span class="question-order">${index + 1}</span></h6>
                    <button type="button" class="btn btn-sm btn-outline-danger btn-remove-question">Remover</button>
                </div>
                <div class="mb-3">
                    <label class="form-label">Enunciado</label>
                    <input type="text" class="form-control question-text" value="${escapeHtml(question.enunciado || '')}" placeholder="Ex.: Verificou nivel de oleo?">
                </div>
                <div class="mb-3">
                    <label class="form-label">Tipo de resposta</label>
                    <select class="form-select question-type">
                        <option value="texto">Input de texto</option>
                        <option value="escolha_unica">Apenas 1 escolha</option>
                        <option value="multipla_escolha">Mais de uma escolha</option>
                    </select>
                </div>
                <div class="mb-3 options-wrapper d-none">
                    <label class="form-label">Opcoes (1 por linha)</label>
                    <textarea class="form-control question-options" rows="3" placeholder="Opcao 1&#10;Opcao 2&#10;Opcao 3"></textarea>
                </div>
                <div class="form-check">
                    <input class="form-check-input question-required" type="checkbox" checked>
                    <label class="form-check-label">Pergunta obrigatoria</label>
                </div>
            </div>
        `;

        const typeSelect = card.querySelector('.question-type');
        const optionsWrapper = card.querySelector('.options-wrapper');
        const optionsTextArea = card.querySelector('.question-options');
        const requiredCheck = card.querySelector('.question-required');

        typeSelect.value = question.tipo || 'texto';
        requiredCheck.checked = question.obrigatoria !== false;
        optionsTextArea.value = Array.isArray(question.opcoes) ? question.opcoes.join('\n') : '';

        const toggleOptions = () => {
            const type = typeSelect.value;
            if (type === 'escolha_unica' || type === 'multipla_escolha') {
                optionsWrapper.classList.remove('d-none');
            } else {
                optionsWrapper.classList.add('d-none');
                optionsTextArea.value = '';
            }
        };

        typeSelect.addEventListener('change', toggleOptions);
        toggleOptions();

        card.querySelector('.btn-remove-question').addEventListener('click', () => {
            card.remove();
            refreshQuestionOrder();
        });

        container.appendChild(card);
        refreshQuestionOrder();
    }

    function refreshQuestionOrder() {
        Array.from(container.children).forEach((card, idx) => {
            const order = card.querySelector('.question-order');
            if (order) {
                order.textContent = String(idx + 1);
            }
        });
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function collectQuestions() {
        const cards = Array.from(container.querySelectorAll('.checklist-question-item'));
        const questions = [];

        for (const [index, card] of cards.entries()) {
            const text = (card.querySelector('.question-text')?.value || '').trim();
            const type = card.querySelector('.question-type')?.value || 'texto';
            const required = !!card.querySelector('.question-required')?.checked;
            const rawOptions = (card.querySelector('.question-options')?.value || '').split('\n');
            const options = rawOptions.map((item) => item.trim()).filter(Boolean);

            if (!text) {
                alert(`Preencha o enunciado da pergunta ${index + 1}.`);
                return null;
            }

            if ((type === 'escolha_unica' || type === 'multipla_escolha') && options.length < 2) {
                alert(`A pergunta ${index + 1} precisa de ao menos 2 opcoes.`);
                return null;
            }

            questions.push({
                enunciado: text,
                tipo: type,
                obrigatoria: required,
                opcoes: type === 'texto' ? [] : options
            });
        }

        if (!questions.length) {
            alert('Adicione ao menos uma pergunta no formulario.');
            return null;
        }

        return questions;
    }

    addButton.addEventListener('click', () => {
        renderQuestionCard();
    });

    form.addEventListener('submit', (event) => {
        const questions = collectQuestions();
        if (!questions) {
            event.preventDefault();
            return;
        }
        hiddenInput.value = JSON.stringify(questions);
    });

    const initialQuestions = parseInitialQuestions();
    if (initialQuestions.length) {
        initialQuestions.forEach((question) => renderQuestionCard(question));
    } else {
        renderQuestionCard();
    }
})();
