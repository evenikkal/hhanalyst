package models

type Vacancy struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Area        Area     `json:"area"`
	Salary      *Salary  `json:"salary"`
	Snippet     Snippet  `json:"snippet"`
	Experience  Exp      `json:"experience"`
	Description string   `json:"description,omitempty"`
}

type Area struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type Salary struct {
	From     *int   `json:"from"`
	To       *int   `json:"to"`
	Currency string `json:"currency"`
}

type Snippet struct {
	Requirement  string `json:"requirement"`
	Responsibility string `json:"responsibility"`
}

type Exp struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type SearchResponse struct {
	Items []Vacancy `json:"items"`
	Found int       `json:"found"`
	Pages int       `json:"pages"`
	Page  int       `json:"page"`
}
