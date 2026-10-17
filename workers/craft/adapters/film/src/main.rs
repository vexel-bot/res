fn main() {
    if std::env::args().nth(1).as_deref() == Some("--version") {
        println!(
            "{} {}",
            clicko_filmcraft_adapter::BUILD,
            clicko_filmcraft_adapter::REVISION
        );
        return;
    }
    let mut adapter = clicko_filmcraft_adapter::Adapter::default();
    if let Err(error) = clicko_craft_protocol::stdio("filmcraft", |method, params| {
        adapter.dispatch(method, params)
    }) {
        eprintln!("FilmCraft adapter transport: {error}");
        std::process::exit(1);
    }
}
