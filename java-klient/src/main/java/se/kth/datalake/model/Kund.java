package se.kth.datalake.model;

public class Kund {
    private Integer id;
    private String namn;
    private String email;
    private String telefon;

    public Integer getId()     { return id; }
    public String getNamn()    { return namn; }
    public String getEmail()   { return email; }
    public String getTelefon() { return telefon; }

    public void setId(Integer id)         { this.id = id; }
    public void setNamn(String namn)       { this.namn = namn; }
    public void setEmail(String email)     { this.email = email; }
    public void setTelefon(String telefon) { this.telefon = telefon; }
}
