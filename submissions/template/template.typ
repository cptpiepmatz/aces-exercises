#import "@preview/oxifmt:0.2.1": strfmt

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
    set text(16pt);
    it + v(1em);
  };

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
