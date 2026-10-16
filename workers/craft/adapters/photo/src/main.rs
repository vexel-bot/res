fn main() {
    if std::env::args().nth(1).as_deref() == Some("--version") {
        println!("{} {}", clicko_photocraft_adapter::BUILD, clicko_photocraft_adapter::REVISION);
        return;
    }
    let mut adapter = clicko_photocraft_adapter::Adapter::default();
    if let Err(error) = clicko_craft_protocol::stdio("photocraft", |method, params| {
        adapter.dispatch(method, params)
    }) {
        eprintln!("PhotoCraft adapter transport: {error}");
        std::process::exit(1);
    }
}
