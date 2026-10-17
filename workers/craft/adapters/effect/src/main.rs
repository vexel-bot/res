fn main() {
    if std::env::args().nth(1).as_deref() == Some("--version") {
        println!(
            "{} {}",
            clicko_effectcraft_adapter::BUILD,
            clicko_effectcraft_adapter::REVISION
        );
        return;
    }
    let mut adapter = clicko_effectcraft_adapter::Adapter::default();
    if let Err(error) = clicko_craft_protocol::stdio("effectcraft", |method, params| {
        adapter.dispatch(method, params)
    }) {
        eprintln!("EffectCraft adapter transport: {error}");
        std::process::exit(1);
    }
}
