import streamlit as st
import requests
import os

st.set_page_config(page_title="Αρχείο Ξυλουργείου", layout="wide")
st.title("🪚 Ψηφιακό Αρχείο Σχεδίων")
st.markdown("Αναζήτησε παραγγελίες με βάση το όνομα του πελάτη, το έπιπλο ή τις διαστάσεις.")

query = st.text_input("🔍 Γράψε αναζήτηση (π.χ. 'Χαλουλός', 'Ντουλάπα'):")

if st.button("Αναζήτηση"):
    if not query.strip():
        st.warning("Παρακαλώ γράψε κάτι για να ψάξεις.")
    else:
        with st.spinner("Ψάχνω στο αρχείο..."):
            try:
                res = requests.get(
                    "http://localhost:8080/api/rag/search",
                    params={"query": query},
                    timeout=30,
                )

                if res.status_code != 200:
                    st.error(f"Σφάλμα Server: {res.status_code}")
                else:
                    results = res.json()

                    if not results:
                        st.warning("Δεν βρέθηκε κανένα σχέδιο με αυτά τα στοιχεία.")
                    else:
                        st.success(f"Βρέθηκαν {len(results)} σχετικά σχέδια!")

                        for r in results:
                            st.markdown("---")
                            st.write(f"📝 **Τι διάβασε το AI:**\n{r['pageInfo']}")

                            # Διαβάζουμε την εικόνα απευθείας από τον δίσκο
                            # για να αποφύγουμε CORS/rendering θέματα του Streamlit
                            local_path = f".{r['imageUrl']}"
                            if os.path.exists(local_path):
                                st.image(local_path)
                            else:
                                st.error(f"Εικόνα δεν βρέθηκε: {local_path}")

            except requests.exceptions.ConnectionError:
                st.error("Δεν μπορώ να συνδεθώ στο Backend (localhost:8080). Είναι ενεργό;")
            except Exception as e:
                st.error(f"Απροσδόκητο σφάλμα: {e}")
