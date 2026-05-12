let tablePedidos;

/* ─── Helpers ─────────────────────────────────────────── */
function fmtBRL(value) {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function getFiltros() {
    return {
        data_inicio: $('#filterDataInicio').val(),
        data_fim:    $('#filterDataFim').val(),
        fornecedor:  $('#filterFornecedor').val(),
        responsavel: $('#filterResponsavel').val(),
        status:      $('#filterStatus').val(),
    };
}

/* ─── DataTable ───────────────────────────────────────── */
$(document).ready(function () {

    // Datas padrão: primeiro e último dia do mês atual
    const hoje = new Date();
    const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    $('#filterDataInicio').val(primeiroDia.toISOString().split('T')[0]);
    $('#filterDataFim').val(hoje.toISOString().split('T')[0]);

    tablePedidos = $('#tabelaPedidos').DataTable({
        responsive: false,
        autoWidth: false,
        lengthMenu: [10, 25, 50, 100],
        pageLength: 25,
        processing: true,
        serverSide: true,
        ajax: {
            url: 'processar',
            type: 'POST',
            data: function (d) {
                const f = getFiltros();
                d.data_inicio  = f.data_inicio;
                d.data_fim     = f.data_fim;
                d.fornecedor   = f.fornecedor;
                d.responsavel  = f.responsavel;
                d.status       = f.status;
            },
        },
        dom: 'lrtip',
        order: [[0, 'desc']],
        columns: [
            { data: 'data_criacao' },
            { data: 'numero_pedido' },
            { data: 'responsavel' },
            { data: 'fornecedor_codigo' },
            { data: 'codigo_produto' },
            {
                data: 'descricao_produto',
                render: function (data) {
                    if (!data) return '';
                    return data.length > 50
                        ? `<span title="${data}">${data.substring(0, 50)}…</span>`
                        : data;
                }
            },
            {
                data: 'valor',
                render: function (data) {
                    return '<span class="fw-semibold">' + fmtBRL(data) + '</span>';
                }
            },
            { data: 'data_aprovacao' },
            { data: 'data_baixa' },
            {
                data: 'status',
                render: function (data, type, row) {
                    const cls = {
                        'Pendente': 'badge-pendente',
                        'Aprovado': 'badge-aprovado',
                        'Baixado':  'badge-baixado',
                    }[data] || 'badge-pendente';
                    return `<span class="badge-status ${cls}">${data}</span>`;
                },
                orderable: false
            },
        ],
        language: {
            lengthMenu:   "Mostrar _MENU_ registros",
            zeroRecords:  "Nenhum pedido encontrado",
            info:         "Página _PAGE_ de _PAGES_",
            infoEmpty:    "Nenhum dado disponível",
            infoFiltered: "(filtrado de _MAX_ registros)",
            paginate:     { previous: "Anterior", next: "Próximo" },
        },
    });

    // Busca textual externa
    $('#searchPedidos').on('keyup', function () {
        tablePedidos.search(this.value).draw();
    });

    // Botão Aplicar
    $('#btnAplicarFiltros').on('click', function () {
        recarregarTudo();
    });

    // Botão Limpar
    $('#btnLimparFiltros').on('click', function () {
        const hoje = new Date();
        const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        $('#filterDataInicio').val(primeiroDia.toISOString().split('T')[0]);
        $('#filterDataFim').val(hoje.toISOString().split('T')[0]);
        $('#filterFornecedor').val('');
        $('#filterResponsavel').val('');
        $('#filterStatus').val('');
        $('#searchPedidos').val('');
        recarregarTudo();
    });

    // Carrega filtros e faz a primeira carga
    carregarOpcoesFilters();
    carregarBigNumbers();
});

/* ─── Recarregar tabela + big numbers ───────────────────── */
function recarregarTudo() {
    tablePedidos.ajax.reload();
    carregarBigNumbers();
}

/* ─── Big numbers ─────────────────────────────────────── */
function carregarBigNumbers() {
    const filtros = getFiltros();

    $.ajax({
        url: 'big-numbers',
        type: 'POST',
        data: {
            csrfmiddlewaretoken: getCsrfToken(),
            ...filtros
        },
        success: function (res) {
            $('#bnTotalValor').text(fmtBRL(res.total_valor));
            $('#bnTotalPedidos').text(res.total_pedidos.toLocaleString('pt-BR'));
            $('#bnTicketMedio').text(fmtBRL(res.ticket_medio));
            $('#bnFornecedores').text(res.fornecedores_unicos.toLocaleString('pt-BR'));
            renderizarRanking(res.ranking);
        },
        error: function () {
            console.error('Erro ao carregar big numbers');
        }
    });
}

/* ─── Ranking ─────────────────────────────────────────── */
function renderizarRanking(ranking) {
    const container = document.getElementById('rankingList');

    if (!ranking || ranking.length === 0) {
        container.innerHTML = '<div class="ranking-empty">Nenhum dado disponível</div>';
        return;
    }

    const maxValor = ranking[0].total;

    const html = ranking.map(function (item, idx) {
        const pos  = idx + 1;
        const pct  = maxValor > 0 ? (item.total / maxValor * 100).toFixed(1) : 0;
        const cls  = pos === 1 ? 'top1' : pos === 2 ? 'top2' : pos === 3 ? 'top3' : '';

        return `
            <div class="ranking-item">
                <div class="ranking-pos ${cls}">${pos}</div>
                <div class="ranking-info">
                    <div class="ranking-name">${item.fornecedor_codigo}</div>
                    <div class="ranking-bar-wrap">
                        <div class="ranking-bar-fill" style="width:${pct}%"></div>
                    </div>
                </div>
                <div class="ranking-values">
                    <div class="ranking-valor">${fmtBRL(item.total)}</div>
                    <div class="ranking-qtd">${item.qtd} pedido${item.qtd !== 1 ? 's' : ''}</div>
                </div>
            </div>`;
    }).join('');

    container.innerHTML = html;
}

/* ─── Carregar opções dos filtros ─────────────────────── */
function carregarOpcoesFilters() {
    $.getJSON('filtros', function (res) {
        const selFornecedor  = document.getElementById('filterFornecedor');
        const selResponsavel = document.getElementById('filterResponsavel');

        (res.fornecedores || []).forEach(function (cod) {
            const opt = document.createElement('option');
            opt.value = cod;
            opt.textContent = cod;
            selFornecedor.appendChild(opt);
        });

        (res.responsaveis || []).forEach(function (nome) {
            const opt = document.createElement('option');
            opt.value = nome;
            opt.textContent = nome;
            selResponsavel.appendChild(opt);
        });
    });
}

/* ─── CSRF token ──────────────────────────────────────── */
function getCsrfToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? cookie.trim().split('=')[1] : '';
}
