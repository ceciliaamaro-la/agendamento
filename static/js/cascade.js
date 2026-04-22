/**
 * Preenchimento em cascata para formulários de Aula / Evento.
 *
 * Procura selects com atributo `data-cascade` (escola, turma, professor,
 * materia, livro) e, ao mudar professor/turma/materia, faz uma chamada AJAX
 * para popular os demais selects.
 *
 * Espera que o template defina window.CASCADE_URLS = {
 *   professor: "/api/cascade/professor/__pk__/",
 *   turma:     "/api/cascade/turma/__pk__/",
 *   materia:   "/api/cascade/materia/__pk__/",
 * }
 */
(function () {
  function $cascade(name) {
    return document.querySelector('select[data-cascade="' + name + '"]');
  }

  function setOptions(select, options, opts) {
    if (!select) return;
    opts = opts || {};
    var keep = opts.keep || false;
    var selected = opts.selected != null ? String(opts.selected) : (keep ? select.value : "");
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
    options.forEach(function (o) {
      var opt = document.createElement("option");
      opt.value = o.id;
      opt.textContent = o.text;
      if (selected && String(o.id) === selected) opt.selected = true;
      select.appendChild(opt);
    });
  }

  function setSingle(select, id, label) {
    if (!select || id == null) return;
    // Garante que a opção exista no select
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
      if (matSel) setOptions(matSel, d.materias, { selected: d.materia_default });
      var turmaSel = $cascade("turma");
      if (turmaSel && d.turmas.length) {
        setOptions(turmaSel, d.turmas, { keep: true });
      }
      var livroSel = $cascade("livro");
      if (livroSel) setOptions(livroSel, d.livros, { keep: true });
    }).catch(function () {});
  }

  function onTurmaChange(e) {
    var pk = e.target.value;
    if (!pk) return;
    fetchJSON(url("turma", pk)).then(function (d) {
      if (!d.ok) return;
      if (d.escola && d.escola.id) setSingle($cascade("escola"), d.escola.id, d.escola.text);
      var profSel = $cascade("professor");
      if (profSel) setOptions(profSel, d.professores, { keep: true });
      var matSel = $cascade("materia");
      if (matSel) setOptions(matSel, d.materias, { keep: true });
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
      if (profSel) setOptions(profSel, d.professores, { keep: true });
      var livroSel = $cascade("livro");
      if (livroSel) setOptions(livroSel, d.livros, { keep: true });
    }).catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    var prof = $cascade("professor");
    var turma = $cascade("turma");
    var mat = $cascade("materia");
    if (prof) prof.addEventListener("change", onProfessorChange);
    if (turma) turma.addEventListener("change", onTurmaChange);
    if (mat) mat.addEventListener("change", onMateriaChange);
  });
})();
