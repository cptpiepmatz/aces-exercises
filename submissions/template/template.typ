#import "@preview/oxifmt:0.2.1": strfmt
#import "@preview/codly:1.0.0": *

#let template(
  course: none,
  authors: none,
  group: none,
  number: none,
  date: datetime.today(),
  tutor: none,
  tutor-mail: none,
  doc
) = {
  set document(
    title: strfmt("{} - Exercise {}", course, number),
    author: authors,
    date: date
  );

  set text(
    size: 14pt,
  );

  let header = align(center, grid(
    columns: (30%, 50fr, 20%),
    rows: 1,
    grid.cell(align: left, image("./des_blau.png")),
    [],
    grid.cell(align: right, image("./uni_logo.png"))
  ));

  let footer = align(top, grid(
    columns: (90%, 10%),
    rows: 1,
    grid.cell(align: left)[
      #number. Exercise for the lecture "#course" \
      Supervisor: #tutor (#link("mailto:" + tutor-mail))
    ],
    grid.cell(align: right, context { here().page() })
  ));

  set page(
    header: header,
    footer: footer,
    margin: (
      top: 140pt,
      bottom: 140pt,
    )
  );

  show heading: it => {
    if it.level == 2 {
      set text(16pt);
    }
    else {
      set text(14pt);
    }
    it + v(1em);
  };

  set quote(block: true, quotes: false)
  show quote: it => {
    block(
      inset: (top: 0.5em, bottom: 0.5em),
      stroke: (left: black), 
      it
    )
  }

  let title() = {
    let title = "Exercise sheet " + str(number);
    let date = date.display("[month repr:long] [day], [year]");

    let title = text(weight: "bold", size: 16pt, title)

    align(center)[#title \ #date]
  };

  let group-block() = block(
    fill: luma(230),
    inset: (x: 16pt, y: 12pt),
    radius: 4pt,
    stroke: black + 1.5pt,
    width: 100%,
    text(size: 16pt)[*Group:* #group \ *Members:* #authors.join(", ")]
  );

  title();
  v(1em);
  group-block();
  v(1em);
  doc
}

#let task(number: none, title) = {
  if type(number) == "integer" {
    counter(heading).update(number - 1);
  }

  if title.has("text") { heading[Task: #title] }
  else { heading[Task] }
}

#let code(
  filename: none, 
  lang: none, 
  show-numbers: true,
  start-line: 1,
  content
) = {
  show: codly-init.with()
  set raw(block: true, lang: lang)
  codly-offset(offset: start-line - 1)
  codly(display-name: false)

  let file-header = box(
    fill: luma(230),
    inset: (left: 8pt, top: 6pt, bottom: -6pt),
    width: 100%,
    strong(filename)
  )

  block(
    fill: luma(230),
    inset: 4pt,
    radius: 8pt, 
    file-header + content
  )
}

#let widget(icon, name, color, content) = {
  let header = strong(text(color, size: 1.1em, icon + " " + name + "\n"))
  block(
    stroke: (left: 3pt + color), width: 100%, inset: 2em, outset: -1em, fill: color.transparentize(70%), above: 0.2em, below: 0.2em, header + block(outset: 0em, inset: 0.3em, above: 1em, below: 0pt, content),
  )
}
