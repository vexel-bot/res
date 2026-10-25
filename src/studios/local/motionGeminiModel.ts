/** Provider failures are sanitized by the backend; never display raw HTTP bodies. */
export function motionGeminiError(message:string) {
  const errors:Record<string,string> = {
    motion_gemini_key_invalid:'A chave parece incompleta ou contém espaços/caracteres inválidos. Cole o valor integral do Google AI Studio; chaves de autorização também são aceitas.',
    motion_gemini_key_required:'Cadastre uma chave própria para este experimento.',
    motion_gemini_free_tier_unverified:'Inferência bloqueada: falta comprovação do Free Tier, das quotas e da autorização no servidor.',
    motion_gemini_not_enabled:'O planejador experimental está desativado.',
    motion_gemini_model_unverified:'Teste a conexão novamente e selecione um modelo retornado pela API.',
    motion_gemini_local_quota_exhausted:'O limite conservador deste experimento foi atingido. Não houve nova inferência.',
    motion_gemini_timeout:'O Gemini não respondeu a tempo. Não haverá repetição automática.',
    llm_provider_http_400:'O modelo recusou o formato solicitado. Nenhuma edição foi aplicada.',
    llm_provider_http_401:'A credencial foi recusada pelo Google.',
    llm_provider_http_403:'A chave não tem acesso a este serviço ou modelo.',
    llm_provider_http_404:'Modelo ou serviço indisponível. Atualize a lista de modelos.',
    llm_provider_http_429:'Quota ou limite de requisições atingido. Nenhum retry será feito.',
    llm_provider_transport_failed:'Falha de comunicação; resultado externo incerto. Não haverá retry automático.',
    llm_provider_invalid_json:'Resposta inválida. O projeto original foi preservado.',
    llm_provider_incomplete_response:'Resposta incompleta. O plano não foi aplicado.',
    motion_gemini_duration_mismatch:'O plano não respeitou a duração solicitada e foi rejeitado.',
  };
  return errors[message] || message;
}
