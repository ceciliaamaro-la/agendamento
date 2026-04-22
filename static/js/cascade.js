/**
 * Preenchimento em cascata para formulários de Aula / Evento.
 *
 * Procura selects com atributo `data-cascade` (escola, turma, professor,
 * materia, livro). Ao mudar professor/turma/materia, faz uma chamada AJAX
 * e popula os demais selects. Quando uma cascata resulta em apenas 1
 * opção, ela é auto-selecionada e dispara seu próprio change em cadeia.
 *
 * Espera que o template defina:
 *   window.CASCADE_URLS = {
 *     professor: "/api/cascade/professor/__pk__/",
 *     turma:     "/api/cascade/turma/__pk__/",
 *     materia:   "/api/cascade/materia/__pk__/",
 *   }
 */
(function () {
  function $cascade(name) {
    return document.querySelector('select[data-cascade="' + name + '"]');
  }

  function fireChange(select) {
    if (!select) return;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }

  /**
   * Substitui as opções do select preservando placeholder.
   * - selected: id a ser pré-selecionado.
   * - keep: se true, tenta manter o valor atual (caso ainda exista).
   * - autoOnSingle: se true e a lista resultar em 1 opção, ela é selecionada.
   */
  function setOptions(select, options, opts) {
    if (!select) return false;
    opts = opts || {};
    // Se a lista vier vazia e o caller pediu para preservar, não toca no select
    if ((!options || options.length === 0) && opts.skipIfEmpty) return false;
    var keep = opts.keep || false;
    var current = select.value;
    var selected = opts.selected != null ? String(opts.selected) : "";
    var placeholder = select.querySelector('option[value=""]');
    select.innerHTML = "";
    if (placeholder) {
      select.appendChild(placeholder);
    } else {
      var blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "---------";
      select.appendChild(blank);
    }
    var matchedSelected = false;
    options.forEach(function (o) {
      var opt = document.createElement("option");
      opt.value = o.id;
      opt.textContent = o.text;
      if (selected && String(o.id) === selected) {
        opt.selected = true; matchedSelected = true;
      } else if (!selected && keep && current && String(o.id) === current) {
        opt.selected = true; matchedSelected = true;
      }
      select.appendChild(opt);
    });
    if (!matchedSelected && opts.autoOnSingle && options.length === 1) {
      select.value = String(options[0].id);
      return true; // auto-selecionou
    }
    return matchedSelected;
  }

  function setSingle(select, id, label) {
    if (!select || id == null) return;
    var found = Array.prototype.find.call(select.options, function (o) {
      return String(o.value) === String(id);
    });
    if (!found && label) {
      var opt = document.createElement("option");
      opt.value = id;
      opt.textContent = label;
      select.appendChild(opt);
    }
    select.value = String(id);
  }

  function fetchJSON(url) {
    return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r); });
  }

  function url(kind, pk) {
    return (window.CASCADE_URLS && window.CASCADE_URLS[kind] || "")
      .replace("__pk__", pk);
  }

  function onProfessorChange(e) {
    var pk = e.target.value;
    if (!pk) return;
    fetchJSON(url("professor", pk)).then(function (d) {
      if (!d.ok) return;
      if (d.escola && d.escola.id) setSingle($cascade("escola"), d.escola.id, d.escola.text);

      var matSel = $cascade("materia");
      var matChanged = setOptions(matSel, d.materias, {
        selected: d.materia_default, autoOnSingle: true,
      });

      var turmaSel = $cascade("turma");
      if (turmaSel && d.turmas.length) {
        setOptions(turmaSel, d.turmas, { keep: true, autoOnSingle: true });
      }

      var livroSel = $cascade("livro");
      setOptions(livroSel, d.livros, {
        selected: d.livro_default, keep: true, autoOnSingle: true,
      });

      // Se a matéria mudou via cascata, dispara a próxima onda
      if (matChanged) fireChange(matSel);
    }).catch(function () {});
  }

  function onTurmaChange(e) {
    var pk = e.target.value;
    if (!pk) return;
    fetchJSON(url("turma", pk)).then(function (d) {
      if (!d.ok) return;
      if (d.escola && d.escola.id) setSingle($cascade("escola"), d.escola.id, d.escola.text);

      var profSel = $cascade("professor");
      var profChanged = setOptions(profSel, d.professores, {
        keep: true, autoOnSingle: true, skipIfEmpty: true,
      });

      var matSel = $cascade("materia");
      var matChanged = setOptions(matSel, d.materias, {
        keep: true, autoOnSingle: true, skipIfEmpty: true,
      });

      // Cascata em cadeia
      if (profChanged) fireChange(profSel);
      else if (matChanged) fireChange(matSel);
    }).catch(function () {});
  }

  function onMateriaChange(e) {
    var pk = e.target.value;
    if (!pk) return;
    var escSel = $cascade("escola");
    var qs = escSel && escSel.value ? ("?escola=" + encodeURIComponent(escSel.value)) : "";
    fetchJSON(url("materia", pk) + qs).then(function (d) {
      if (!d.ok) return;
      var profSel = $cascade("professor");
      setOptions(profSel, d.professores, {
        keep: true, autoOnSingle: true, skipIfEmpty: true,
      });

      var livroSel = $cascade("livro");
      setOptions(livroSel, d.livros, {
        selected: d.livro_default, keep: true, autoOnSingle: true, skipIfEmpty: true,
      });
    }).catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    var prof  = $cascade("professor");
    var turma = $cascade("turma");
    var mat   = $cascade("materia");
    if (prof)  prof.addEventListener("change", onProfessorChange);
    if (turma) turma.addEventListener("change", onTurmaChange);
    if (mat)   mat.addEventListener("change", onMateriaChange);

    // Boot: se já vem com professor pré-selecionado (ex. professor_vinculado),
    // dispara a cascata para preencher escola/matéria/livros automaticamente.
    if (prof && prof.value) fireChange(prof);
    else if (turma && turma.value) fireChange(turma);
  });
})();
